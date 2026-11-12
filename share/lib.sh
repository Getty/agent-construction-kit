# Shared functions of agent-construction-kit. Sourced, never executed.
# bash 3.2 compatible: no associative arrays, no mapfile, no ${var,,}.

# Keys a definition may carry besides its own; used to accept env overrides
# (<PREFIX>_<KEY>) for keys the definition does not mention.
ACK_KNOWN_KEYS="DESCRIPTION KEY_VAR KEY_FILE KEY_FILE_VAR KEY_REQUIRED AUTH_TOKEN PREFLIGHT PROXY_PORT BARE MCP_CONFIG BASE_URL MODEL OPUS_MODEL SONNET_MODEL HAIKU_MODEL FABLE_MODEL OPUS_MODEL_NAME SONNET_MODEL_NAME HAIKU_MODEL_NAME FABLE_MODEL_NAME SMALL_MODEL SUBAGENT_MODEL CO_AUTHORED_BY API_TIMEOUT_MS CONTEXT_WINDOW MAX_CONTEXT_TOKENS AUTOCOMPACT_PCT MAX_OUTPUT_TOKENS MAX_THINKING_TOKENS EFFORT_LEVEL MAX_TOOL_CHAR_BUDGET TOOL_SEARCH DISABLE_NONESSENTIAL_TRAFFIC DISABLE_EXPERIMENTAL_BETAS UNKNOWN_MODEL_WINDOW"

ack_paths() {
  ACK_DATA_DIR="${ACK_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/agent-construction-kit}"
  ACK_CONFIG_DIR="${ACK_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/agent-construction-kit}"
  ACK_STATE_DIR="${ACK_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-construction-kit}"
}

# _ack_trim STRING -> REPLY (no fork); ack_trim prints it.
_ack_trim() {
  REPLY="$1"
  REPLY="${REPLY//$'\r'/}"
  REPLY="${REPLY#"${REPLY%%[![:space:]]*}"}"
  REPLY="${REPLY%"${REPLY##*[![:space:]]}"}"
}
ack_trim() { _ack_trim "$1"; printf '%s' "$REPLY"; }

# ack_conf KEY -> resolved value of the loaded provider, empty if unset
ack_conf() {
  local n="ACK_C_$1"
  printf '%s' "${!n}"
}

# Maps a definition key to the variable it exports; fails for control keys.
_ack_export_name() {
  case "$1" in
    BASE_URL) REPLY=ANTHROPIC_BASE_URL ;;
    MODEL) REPLY="ANTHROPIC_MODEL" ;;
    OPUS_MODEL|SONNET_MODEL|HAIKU_MODEL|FABLE_MODEL) REPLY="ANTHROPIC_DEFAULT_$1" ;;
    OPUS_MODEL_NAME|SONNET_MODEL_NAME|HAIKU_MODEL_NAME|FABLE_MODEL_NAME) REPLY="ANTHROPIC_DEFAULT_$1" ;;
    SMALL_MODEL) REPLY="ANTHROPIC_SMALL_FAST_MODEL" ;;
    SUBAGENT_MODEL) REPLY="CLAUDE_CODE_SUBAGENT_MODEL" ;;
    CO_AUTHORED_BY) REPLY="CO_AUTHORED_BY" ;;
    API_TIMEOUT_MS) REPLY="API_TIMEOUT_MS" ;;
    CONTEXT_WINDOW) REPLY="CLAUDE_CODE_AUTO_COMPACT_WINDOW" ;;
    MAX_CONTEXT_TOKENS) REPLY="CLAUDE_CODE_MAX_CONTEXT_TOKENS" ;;
    AUTOCOMPACT_PCT) REPLY="CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" ;;
    MAX_OUTPUT_TOKENS) REPLY="CLAUDE_CODE_MAX_OUTPUT_TOKENS" ;;
    MAX_THINKING_TOKENS) REPLY="MAX_THINKING_TOKENS" ;;
    EFFORT_LEVEL) REPLY="CLAUDE_CODE_EFFORT_LEVEL" ;;
    MAX_TOOL_CHAR_BUDGET) REPLY="SLASH_COMMAND_TOOL_CHAR_BUDGET" ;;
    TOOL_SEARCH) REPLY="ENABLE_TOOL_SEARCH" ;;
    DISABLE_NONESSENTIAL_TRAFFIC) REPLY="CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" ;;
    DISABLE_EXPERIMENTAL_BETAS) REPLY="CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS" ;;
    UNKNOWN_MODEL_WINDOW) REPLY="CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT" ;;
    *) return 1 ;;
  esac
}

ack_export_name() { _ack_export_name "$1" && printf '%s\n' "$REPLY"; }

# _ack_build_exports -> ACK_EXPORTS: NAME=VALUE lines for every set exportable key (no fork)
_ack_build_exports() {
  local k v
  ACK_EXPORTS=""
  for k in $ACK_KEYS; do
    _ack_export_name "$k" || continue
    v="ACK_C_$k"; v="${!v}"
    [ -n "$v" ] && ACK_EXPORTS="$ACK_EXPORTS$REPLY=$v"$'\n'
  done
  return 0
}

# ack_exports -> prints NAME=VALUE for every set exportable key of the loaded provider
ack_exports() { _ack_build_exports; printf '%s' "$ACK_EXPORTS"; }

# Parses one definition file into ACK_R_<KEY> (later calls override earlier ones).
# ACK_FILE_KEYS lists the keys this one file set.
_ack_read_def() {
  local file="$1" line key val n=0
  ACK_FILE_KEYS=""
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    _ack_trim "$line"; line="$REPLY"
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in
      *=*) ;;
      *) echo "ack: line $n of '$file' is not KEY=VALUE." >&2
         echo "ack: fix or remove that line in the definition." >&2
         return 2 ;;
    esac
    _ack_trim "${line%%=*}"; key="$REPLY"
    val="${line#*=}"
    val="${val%%[[:space:]]#*}"
    _ack_trim "$val"; val="$REPLY"
    case "$key" in
      ''|*[!A-Z_]*)
        echo "ack: '$key' in '$file' is not a valid key name (only A-Z and _)." >&2
        echo "ack: rename the key in the definition." >&2
        return 2 ;;
    esac
    case " $ACK_KEYS " in *" $key "*) ;; *) ACK_KEYS="$ACK_KEYS $key" ;; esac
    ACK_FILE_KEYS="$ACK_FILE_KEYS $key"
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
  ACK_MCP_DIR="$base/providers"
  shipped="$base/providers/$name.conf"
  user="$ACK_CONFIG_DIR/providers/$name.conf"
  if [ -f "$shipped" ]; then found=1; _ack_read_def "$shipped" || return 2; fi
  if [ -f "$user" ]; then
    found=1; _ack_read_def "$user" || return 2
    case "$ACK_FILE_KEYS " in *" MCP_CONFIG "*) ACK_MCP_DIR="$ACK_CONFIG_DIR/providers" ;; esac
  fi
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
      [ "$k" = MCP_CONFIG ] && ACK_MCP_DIR="$ACK_CONFIG_DIR/providers"
    fi
  done
  for k in $ACK_KEYS; do _ack_resolve "$k" || return 2; done
  # defaults
  [ -n "$ACK_C_KEY_FILE_VAR" ] || ACK_C_KEY_FILE_VAR="$ACK_C_KEY_VAR"
  [ -n "$ACK_C_KEY_FILE" ] || ACK_C_KEY_FILE="$ACK_CONFIG_DIR/$name.env"
  [ -n "$ACK_C_KEY_REQUIRED" ] || ACK_C_KEY_REQUIRED=1
  for k in KEY_FILE_VAR KEY_FILE KEY_REQUIRED; do
    case " $ACK_KEYS " in *" $k "*) ;; *) ACK_KEYS="$ACK_KEYS $k" ;; esac
  done
  ACK_PROVIDER="$name"
  return 0
}

# ack_mcp_path -> REPLY: absolute path of the loaded provider's MCP file, found next to
# the definition that sets MCP_CONFIG (user overlay or environment: the user providers
# directory; otherwise the shipped one). REPLY is empty when MCP_CONFIG is unset.
# Returns 2 (message on stderr) for a name with a path in it or a missing file.
ack_mcp_path() {
  local m="$ACK_C_MCP_CONFIG"
  REPLY=""
  [ -n "$m" ] || return 0
  case "$m" in
    */*|*\\*|*..*)
      echo "ack: MCP_CONFIG '$m' is not a plain file name (no / and no ..)." >&2
      echo "ack: put the file next to the definition and give only its name." >&2
      return 2 ;;
  esac
  if [ ! -f "$ACK_MCP_DIR/$m" ]; then
    echo "ack: the MCP file '$ACK_MCP_DIR/$m' does not exist." >&2
    echo "ack: create it there, or fix MCP_CONFIG in the definition." >&2
    return 2
  fi
  REPLY="$ACK_MCP_DIR/$m"
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
  local file="$1" var="$2" line v found=1 out="" first=1 bom=$'\xef\xbb\xbf'
  [ -f "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$first" = 1 ]; then line="${line#"$bom"}"; first=0; fi
    _ack_trim "$line"; line="$REPLY"
    case "$line" in 'export'[[:space:]]*) _ack_trim "${line#export}"; line="$REPLY" ;; esac
    case "$line" in
      "$var"=*)
        _ack_trim "${line#*=}"; v="$REPLY"
        case "$v" in
          \"*) v="${v#\"}"; case "$v" in *\"*) v="${v%%\"*}" ;; esac ;;
          \'*) v="${v#\'}"; case "$v" in *\'*) v="${v%%\'*}" ;; esac ;;
          *) v="${v%%[[:space:]]#*}"; _ack_trim "$v"; v="$REPLY" ;;
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

# ---------------------------------------------------------------- proxy

ACK_PROXY_UNIT="claude-code-proxy.service"

# ack_has_user_service: a user service manager is here (Linux with systemctl).
# ACK_UNAME pins the OS name for tests.
ack_has_user_service() {
  [ "${ACK_UNAME:-$(uname -s)}" = Linux ] || return 1
  [ -n "$(type -P systemctl 2>/dev/null)" ]
}

# ack_proxy_unit_file -> prints the path of the user unit
ack_proxy_unit_file() { printf '%s' "$HOME/.config/systemd/user/$ACK_PROXY_UNIT"; }

# ack_proxy_reachable PORT: 0 when 127.0.0.1:PORT answers with any HTTP status.
# --noproxy: a gateway's own 502 must not count as an answer.
ack_proxy_reachable() {
  if [ -z "$(type -P curl 2>/dev/null)" ]; then
    if [ -z "${ACK_CURL_WARNED:-}" ]; then
      ACK_CURL_WARNED=1
      echo "ack: curl is not installed, so the proxy cannot be probed." >&2
      echo "ack: install curl and try again." >&2
    fi
    return 1
  fi
  curl -s -o /dev/null --max-time 2 --noproxy '*' "http://127.0.0.1:$1/"
}

# ack_run_bounded SECS CMD [ARGS...]: run CMD for at most SECS seconds (no timeout
# binary needed). Sets ACK_BOUNDED_OUT (stdout), ACK_BOUNDED_ERR (first stderr line);
# returns the exit status, 124 on timeout.
ack_run_bounded() {
  local secs="$1" d pid i=0 max rc
  shift
  ACK_BOUNDED_OUT="" ACK_BOUNDED_ERR=""
  d="$(mktemp -d)" || return 1
  "$@" >"$d/out" 2>"$d/err" </dev/null &
  pid=$!
  max=$((secs * 10))
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt "$max" ]; do
    sleep 0.1
    i=$((i + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    rc=124
  else
    wait "$pid"; rc=$?
  fi
  ACK_BOUNDED_OUT="$(cat "$d/out" 2>/dev/null)"
  IFS= read -r ACK_BOUNDED_ERR < "$d/err" 2>/dev/null
  ACK_BOUNDED_ERR="${ACK_BOUNDED_ERR//$'\r'/}"
  rm -rf "$d"
  return "$rc"
}

# _ack_proxy_wait PORT [PID]: up to 10 rounds of 0.5 s until the proxy answers;
# stops at once when PID (the process just started) is gone.
_ack_proxy_wait() {
  local i=0
  while [ "$i" -lt 10 ]; do
    ack_proxy_reachable "$1" && return 0
    if [ -n "$2" ] && ! kill -0 "$2" 2>/dev/null; then
      ack_proxy_reachable "$1"
      return
    fi
    sleep 0.5
    i=$((i + 1))
  done
  ack_proxy_reachable "$1"
}

# ack_proxy_ensure PORT: make the proxy answer on PORT; 5 when that fails.
ack_proxy_ensure() {
  local port="$1" bin log sz pid
  if [ -z "$port" ]; then
    echo "ack: the provider has no PROXY_PORT, so the proxy cannot be started." >&2
    echo "ack: set PROXY_PORT=... in its definition." >&2
    return 5
  fi
  ack_proxy_reachable "$port" && return 0
  ack_paths
  if ack_has_user_service && [ -f "$(ack_proxy_unit_file)" ]; then
    if systemctl --user start "$ACK_PROXY_UNIT" >/dev/null 2>&1; then
      if _ack_proxy_wait "$port"; then return 0; fi
      echo "ack: the proxy service was started but nothing answers on port $port." >&2
      echo "ack: check it with: systemctl --user status $ACK_PROXY_UNIT" >&2
      return 5
    fi
    echo "ack: systemctl --user could not start $ACK_PROXY_UNIT (no user service manager session?); starting the proxy directly." >&2
  fi
  bin="$(type -P claude-code-proxy 2>/dev/null)"
  if [ -z "$bin" ]; then
    echo "ack: claude-code-proxy is not installed." >&2
    echo "ack: install it (see the skill's references/openai-proxy.md), then try again." >&2
    return 5
  fi
  mkdir -p "$ACK_STATE_DIR" || return 5
  log="$ACK_STATE_DIR/proxy.log"
  if [ -f "$log" ]; then
    sz="$(wc -c < "$log")"; sz="${sz//[[:space:]]/}"
    if [ "${sz:-0}" -gt 1048576 ]; then : > "$log"; fi
  fi
  nohup "$bin" serve --no-monitor --port "$port" >>"$log" 2>&1 </dev/null &
  pid=$!
  if _ack_proxy_wait "$port" "$pid"; then return 0; fi
  if ! ack_run_bounded 20 "$bin" codex auth status; then
    echo "ack: The proxy is not signed in. Run: claude-code-proxy codex auth login" >&2
    return 5
  fi
  echo "ack: the proxy was started but nothing answers on port $port." >&2
  echo "ack: read the log at $log." >&2
  return 5
}
