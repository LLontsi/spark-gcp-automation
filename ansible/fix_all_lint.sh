#!/bin/bash
set -e

echo "🔧 Fixing all ansible-lint issues..."

# 1. Remove trailing spaces
echo "✓ Removing trailing spaces..."
find . -name "*.yml" -type f -exec sed -i 's/[[:space:]]*$//' {} +

# 2. Add newline at end of files
echo "✓ Adding newlines at end of files..."
find . -name "*.yml" -type f -exec sh -c '
  for file; do
    if [ -n "$(tail -c1 "$file")" ]; then
      echo "" >> "$file"
    fi
  done
' sh {} +

# 3. Fix empty lines (remove multiple consecutive blank lines)
echo "✓ Fixing empty lines..."
find . -name "*.yml" -type f -exec sed -i '/^$/N;/^\n$/D' {} +

# 4. Rename hdfs-setup to hdfs_setup
if [ -d "roles/hdfs-setup" ]; then
    echo "✓ Renaming hdfs-setup → hdfs_setup..."
    mv roles/hdfs-setup roles/hdfs_setup
    find playbooks/ -name "*.yml" -exec sed -i 's/hdfs-setup/hdfs_setup/g' {} +
fi

# 5. Fix truthy values (yes/no → true/false)
echo "✓ Fixing truthy values..."
find roles/ playbooks/ -name "*.yml" -exec sed -i \
  -e "s/: yes$/: true/g" \
  -e "s/: no$/: false/g" \
  -e "s/: Yes$/: true/g" \
  -e "s/: No$/: false/g" \
  -e "s/: on$/: true/g" \
  -e "s/: off$/: false/g" {} +

# 6. Remove strategy: free from playbooks
echo "✓ Removing strategy: free..."
find playbooks/ -name "*.yml" -exec sed -i '/^[[:space:]]*strategy:[[:space:]]*free/d' {} +

# 7. Add missing newlines to specific files
for file in roles/grafana/tasks/main.yml \
            roles/grafana/handlers/main.yml \
            roles/hdfs_setup/tasks/main.yml \
            inventory/gcp.yml; do
    if [ -f "$file" ]; then
        if [ -n "$(tail -c1 "$file")" ]; then
            echo "" >> "$file"
            echo "✓ Added newline to $file"
        fi
    fi
done

echo ""
echo "✅ All automatic fixes applied!"
echo ""
echo "Next steps:"
echo "  1. git add ansible/"
echo "  2. git commit -m 'fix(ansible): resolve all lint issues'"
echo "  3. git push"

