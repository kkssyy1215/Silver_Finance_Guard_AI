#!/usr/bin/env sh

set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
archive_dir="$project_root/deliverables"
archive_path="$archive_dir/Silver_Finance_Guard_AI_Submission_Source.zip"
stage_dir=$(mktemp -d "${TMPDIR:-/tmp}/silver-finance-guard-submission.XXXXXX")
package_dir="$stage_dir/Silver_Finance_Guard_AI"

cleanup() {
  rm -rf "$stage_dir"
}

trap cleanup EXIT INT TERM

mkdir -p "$package_dir"

copy_item() {
  cp -R "$project_root/$1" "$package_dir/$1"
}

for item in \
  backend \
  frontend \
  docs \
  README.md \
  SUBMISSION.md \
  LICENSE \
  PRIVACY.md \
  TERMS.md \
  THIRD_PARTY_NOTICES.md \
  Dockerfile \
  render.yaml \
  pytest.ini \
  .dockerignore \
  .gitattributes \
  .gitignore
do
  copy_item "$item"
done

mkdir -p "$package_dir/tools"
copy_item "tools/evaluate_risk_detection.py"
copy_item "tools/create_submission_archive.sh"

find "$package_dir" \
  \( -name .venv -o -name node_modules -o -name .next -o -name out -o -name .pytest_cache -o -name __pycache__ \) \
  -type d -prune -exec rm -rf {} +
find "$package_dir" -name .DS_Store -type f -delete
rm -f "$package_dir/deliverables/Silver_Finance_Guard_AI_Submission_Source.zip"

mkdir -p "$archive_dir"
rm -f "$archive_path"
(cd "$stage_dir" && zip -qr "$archive_path" Silver_Finance_Guard_AI)

echo "Created $archive_path"
