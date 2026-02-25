#!/usr/bin/env bash

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

tmux set-option -goq @copilot_usage_scope "auto"
tmux set-option -goq @copilot_usage_org ""
tmux set-option -goq @copilot_usage_refresh_seconds "90"
tmux set-option -goq @copilot_usage_cache_file "$HOME/.cache/copilot-usage/status.json"
tmux set-option -goq @copilot_usage_python "python3"
tmux set-option -goq @copilot_usage_token ""
tmux set-option -goq @copilot_usage_show_model "off"
tmux set-option -goq @copilot_usage_auto_append "on"
tmux set-option -goq @copilot_usage_monthly_limit "0"
tmux set-option -goq @copilot_usage_bar_width "10"
tmux set-option -goq @copilot_usage_percent_metric "total"

python_bin="$(tmux show-option -gv @copilot_usage_python)"
scope="$(tmux show-option -gv @copilot_usage_scope)"
org="$(tmux show-option -gv @copilot_usage_org)"
refresh="$(tmux show-option -gv @copilot_usage_refresh_seconds)"
cache_file="$(tmux show-option -gv @copilot_usage_cache_file)"
token="$(tmux show-option -gv @copilot_usage_token)"
show_model="$(tmux show-option -gv @copilot_usage_show_model)"
monthly_limit="$(tmux show-option -gv @copilot_usage_monthly_limit)"
bar_width="$(tmux show-option -gv @copilot_usage_bar_width)"
percent_metric="$(tmux show-option -gv @copilot_usage_percent_metric)"

render_cmd="$python_bin $PLUGIN_DIR/bin/render_status.py --cache-file $cache_file --monthly-limit $monthly_limit --bar-width $bar_width --percent-metric $percent_metric"
if [[ "$show_model" == "on" ]]; then
  render_cmd="$render_cmd --show-model"
fi
segment="#($render_cmd)"

status_right="$(tmux show-option -gv status-right)"
auto_append="$(tmux show-option -gv @copilot_usage_auto_append)"
if [[ "$auto_append" == "on" ]] && [[ "$status_right" != *"render_status.py"* ]]; then
  tmux set-option -gq status-right "$status_right $segment"
fi

updater_cmd="$python_bin $PLUGIN_DIR/bin/updater.py --scope $scope --cache-file $cache_file --refresh-seconds $refresh --python $python_bin"
if [[ -n "$org" ]]; then
  updater_cmd="$updater_cmd --org $org"
fi
if [[ -n "$token" ]]; then
  updater_cmd="$updater_cmd --token $token"
fi

tmux run-shell -b "$updater_cmd"
