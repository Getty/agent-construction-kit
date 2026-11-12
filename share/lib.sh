# Shared functions of agent-construction-kit. Sourced, never executed.
# bash 3.2 compatible: no associative arrays, no mapfile, no ${var,,}.

# Keys a definition may carry besides its own; used to accept env overrides
# (<PREFIX>_<KEY>) for keys the definition does not mention.
ACK_KNOWN_KEYS="DESCRIPTION KEY_VAR KEY_FILE KEY_FILE_VAR KEY_REQUIRED AUTH_TOKEN PREFLIGHT PROXY_PORT BARE BASE_URL MODEL OPUS_MODEL SONNET_MODEL HAIKU_MODEL FABLE_MODEL OPUS_MODEL_NAME SONNET_MODEL_NAME HAIKU_MODEL_NAME FABLE_MODEL_NAME SMALL_MODEL SUBAGENT_MODEL CO_AUTHORED_BY API_TIMEOUT_MS CONTEXT_WINDOW MAX_CONTEXT_TOKENS AUTOCOMPACT_PCT MAX_OUTPUT_TOKENS MAX_THINKING_TOKENS EFFORT_LEVEL MAX_TOOL_CHAR_BUDGET TOOL_SEARCH DISABLE_NONESSENTIAL_TRAFFIC DISABLE_EXPERIMENTAL_BETAS UNKNOWN_MODEL_WINDOW"

ack_paths() {
  ACK_DATA_DIR="${ACK_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/agent-construction-kit}"
  ACK_CONFIG_DIR="${ACK_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/agent-construction-kit}"
  ACK_STATE_DIR="${ACK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-construction-kit}"
}

# ack_trim STRING -> prints STRING without surrounding whitespace and CR
ack_trim() {
  local v="$1"
  v="${v//$'\r'/}"
  v="${v#"${v%%[![:space:]]*}"}"
  v="${v%"${v##*[![:space:]]}"}"
  printf '%s' "$v"
}

# ack_conf KEY -> resolved value of the loaded provider, empty if unset
ack_conf() {
  local n="ACK_C_$1"
  printf '%s' "${!n}"
}

# Maps a definition key to the variable it exports; fails for control keys.
ack_export_name() {
  case "$1" in
    BASE_URL) echo ANTHROPIC_BASE_URL ;;
    MODEL) echo ANTHROPIC_MODEL ;;
    OPUS_MODEL|SONNET_MODEL|HAIKU_MODEL|FABLE_MODEL) echo "ANTHROPIC_DEFAULT_$1" ;;
    OPUS_MODEL_NAME|SONNET_MODEL_NAME|HAIKU_MODEL_NAME|FABLE_MODEL_NAME) echo "ANTHROPIC_DEFAULT_$1" ;;
    SMALL_MODEL) echo ANTHROPIC_SMALL_FAST_MODEL ;;
    SUBAGENT_MODEL) echo CLAUDE_CODE_SUBAGENT_MODEL ;;
    CO_AUTHORED_BY) echo CO_AUTHORED_BY ;;
    API_TIMEOUT_MS) echo API_TIMEOUT_MS ;;
    CONTEXT_WINDOW) echo CLAUDE_CODE_AUTO_COMPACT_WINDOW ;;
    MAX_CONTEXT_TOKENS) echo CLAUDE_CODE_MAX_CONTEXT_TOKENS ;;
    AUTOCOMPACT_PCT) echo CLAUDE_AUTOCOMPACT_PCT_OVERRIDE ;;
    MAX_OUTPUT_TOKENS) echo CLAUDE_CODE_MAX_OUTPUT_TOKENS ;;
    MAX_THINKING_TOKENS) echo MAX_THINKING_TOKENS ;;
    EFFORT_LEVEL) echo CLAUDE_CODE_EFFORT_LEVEL ;;
    MAX_TOOL_CHAR_BUDGET) echo SLASH_COMMAND_TOOL_CHAR_BUDGET ;;
    TOOL_SEARCH) echo ENABLE_TOOL_SEARCH ;;
    DISABLE_NONESSENTIAL_TRAFFIC) echo CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC ;;
    DISABLE_EXPERIMENTAL_BETAS) echo CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS ;;
    UNKNOWN_MODEL_WINDOW) echo CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT ;;
    *) return 1 ;;
  esac
}

# ack_exports -> prints NAME=VALUE for every set exportable key of the loaded provider
ack_exports() {
  local k name v
  for k in $ACK_KEYS; do
    name="$(ack_export_name "$k")" || continue
    v="$(ack_conf "$k")"
    [ -n "$v" ] && printf '%s=%s\n' "$name" "$v"
  done
  return 0
}

# Parses one definition file into ACK_R_<KEY> (later calls override earlier ones).
_ack_read_def() {
  local file="$1" line key val n=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    line="$(ack_trim "$line")"
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in
      *=*) ;;
      *) echo "ack: line $n of '$file' is not KEY=VALUE." >&2
         echo "ack: fix or remove that line in the definition." >&2
         return 2 ;;
    esac
    key="$(ack_trim "${line%%=*}")"
    val="${line#*=}"
    val="${val%%[[:space:]]#*}"
    val="$(ack_trim "$val")"
    case "$key" in
      ''|*[!A-Z_]*)
        echo "ack: '$key' in '$file' is not a valid key name (only A-Z and _)." >&2
        echo "ack: rename the key in the definition." >&2
        return 2 ;;
    esac
    case " $ACK_KEYS " in *" $key "*) ;; *) ACK_KEYS="$ACK_KEYS $key" ;; esac
    printf -v "ACK_R_$key" '%s' "$val"
  done < "$file"
  return 0
}

# Resolves ${KEY} references of KEY into ACK_C_<KEY>.
_ack_resolve() {
  local key="$1" st="ACK_S_$1" raw="ACK_R_$1" val out ref refval
  case "${!st}" in
    2) return 0 ;;
    1) echo "ack: the value of $key refers to itself through \${...} references." >&2
       echo "ack: break the loop in the definition." >&2
       return 2 ;;
  esac
  printf -v "$st" '%s' 1
  val="${!raw}"
  out=""
  while :; do
    case "$val" in
      *'${'*) ;;
      *) break ;;
    esac
    out="$out${val%%\$\{*}"
    val="${val#*\$\{}"
    case "$val" in
      *'}'*) ;;
      *) echo "ack: unterminated \${ in the value of $key." >&2
         echo "ack: close the reference with }." >&2
         return 2 ;;
    esac
    ref="${val%%\}*}"
    val="${val#*\}}"
    case "$ref" in
      ''|*[!A-Z_]*)
        echo "ack: '\${$ref}' in the value of $key is not a key name." >&2
        echo "ack: use \${KEY} with a key of the same definition." >&2
        return 2 ;;
    esac
    case " $ACK_KEYS " in
      *" $ref "*) ;;
      *) echo "ack: the value of $key refers to unknown key \${$ref}." >&2
         echo "ack: define $ref in the definition or remove the reference." >&2
         return 2 ;;
    esac
    _ack_resolve "$ref" || return 2
    refval="ACK_C_$ref"
    out="$out${!refval}"
  done
  printf -v "ACK_C_$key" '%s' "$out$val"
  printf -v "$st" '%s' 2
  return 0
}

# ack_provider_load NAME BASEDIR
ack_provider_load() {
  local name="$1" base="$2" shipped user found=0 k p envn
  ack_paths
  case "$name" in
    ''|*[!a-z0-9_-]*|-*)
      echo "ack: '$name' is not a valid provider name (a-z, 0-9, - and _)." >&2
      echo "ack: pick a name from the list of providers." >&2
      return 2 ;;
  esac
  # forget a previously loaded provider
  for k in $ACK_KEYS; do unset "ACK_R_$k" "ACK_C_$k" "ACK_S_$k"; done
  ACK_KEYS=""
  shipped="$base/providers/$name.conf"
  user="$ACK_CONFIG_DIR/providers/$name.conf"
  if [ -f "$shipped" ]; then found=1; _ack_read_def "$shipped" || return 2; fi
  if [ -f "$user" ]; then found=1; _ack_read_def "$user" || return 2; fi
  if [ "$found" = 0 ]; then
    echo "ack: no provider named '$name' (looked for $shipped and $user)." >&2
    echo "ack: choose one of: $(ack_provider_names "$base" | tr '\n' ' ')" >&2
    return 2
  fi
  p="$ACK_R_PREFIX"
  case "$p" in
    ''|*[!A-Z0-9_]*)
      echo "ack: provider '$name' has no valid PREFIX (A-Z, 0-9, _)." >&2
      echo "ack: set PREFIX=... in its definition." >&2
      return 2 ;;
  esac
  # environment layer: <PREFIX>_<KEY>, also for known keys the definition omits
  for k in $ACK_KNOWN_KEYS $ACK_KEYS; do
    [ "$k" = PREFIX ] && continue
    envn="${p}_$k"
    if [ -n "${!envn+x}" ]; then
      case " $ACK_KEYS " in *" $k "*) ;; *) ACK_KEYS="$ACK_KEYS $k" ;; esac
      printf -v "ACK_R_$k" '%s' "${!envn}"
    fi
  done
  for k in $ACK_KEYS; do _ack_resolve "$k" || return 2; done
  # defaults
  [ -n "$(ack_conf KEY_FILE_VAR)" ] || printf -v ACK_C_KEY_FILE_VAR '%s' "$(ack_conf KEY_VAR)"
  [ -n "$(ack_conf KEY_FILE)" ] || printf -v ACK_C_KEY_FILE '%s' "$ACK_CONFIG_DIR/$name.env"
  [ -n "$(ack_conf KEY_REQUIRED)" ] || printf -v ACK_C_KEY_REQUIRED '%s' 1
  for k in KEY_FILE_VAR KEY_FILE KEY_REQUIRED; do
    case " $ACK_KEYS " in *" $k "*) ;; *) ACK_KEYS="$ACK_KEYS $k" ;; esac
  done
  ACK_PROVIDER="$name"
  return 0
}

# ack_provider_names BASEDIR
ack_provider_names() {
  ack_paths
  local f
  for f in "$1"/providers/*.conf "$ACK_CONFIG_DIR"/providers/*.conf; do
    [ -f "$f" ] || continue
    f="${f##*/}"
    printf '%s\n' "${f%.conf}"
  done | LC_ALL=C sort -u
}

# ack_key_read FILE VAR -> prints the value of VAR in FILE (last assignment wins)
ack_key_read() {
  local file="$1" var="$2" line v found=1 out=""
  [ -f "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="$(ack_trim "$line")"
    case "$line" in 'export'[[:space:]]*) line="$(ack_trim "${line#export}")" ;; esac
    case "$line" in
      "$var"=*)
        v="$(ack_trim "${line#*=}")"
        case "$v" in
          \"*\") v="${v#\"}"; v="${v%\"}" ;;
          \'*\') v="${v#\'}"; v="${v%\'}" ;;
        esac
        out="$v"; found=0 ;;
    esac
  done < "$file"
  [ "$found" = 0 ] && printf '%s' "$out"
  return "$found"
}

# ack_find_claude -> prints the path of claude
ack_find_claude() {
  local p
  if [ -n "${ACK_CLAUDE_BIN:-}" ]; then
    [ -x "$ACK_CLAUDE_BIN" ] || return 1
    printf '%s\n' "$ACK_CLAUDE_BIN"
    return 0
  fi
  p="$(type -P claude 2>/dev/null)"
  if [ -z "$p" ]; then
    for p in "$HOME/.local/bin/claude" "$HOME/bin/claude"; do
      [ -x "$p" ] && break
      p=""
    done
  fi
  [ -n "$p" ] || return 1
  printf '%s\n' "$p"
}
