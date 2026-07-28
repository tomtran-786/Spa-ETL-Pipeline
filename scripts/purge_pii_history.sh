#!/usr/bin/env bash
#
# Gỡ dữ liệu khách hàng khỏi git — file đang track VÀ toàn bộ lịch sử.
#
# VÌ SAO CẦN: repo từng để public. Trên GitHub hiện có tên + SĐT của ~6.300
# lead và ~1.700 hóa đơn. Chuyển repo sang private KHÔNG xóa được phần đã nằm
# trong lịch sử — ai đã clone/fork lúc còn public vẫn giữ bản sao, và bất kỳ ai
# được cấp quyền vào repo sau này vẫn đọc được toàn bộ dữ liệu cũ.
#
# .gitignore KHÔNG giải quyết được việc này: nó chỉ chặn file MỚI, không gỡ
# file đã được track.
#
# CÁCH CHẠY:
#     bash scripts/purge_pii_history.sh
#
# Script tự dừng ở từng bước để bạn xem trước khi làm tiếp. Bước cuối
# (force-push) script KHÔNG tự làm — bạn phải tự chạy sau khi đã kiểm.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# Các đường dẫn chứa dữ liệu khách. Thêm vào đây nếu phát sinh file mới.
PII_PATHS=(
  "kiotviet.csv"
  "ĐĂT HẸN .csv"
  "Sales_Marketing dataset - SALE T1-2-3_2026.csv"
  "Sales_Marketing dataset - ĐĂT HẸN .csv"
  "BÁO CÁO TỔNG HỢP SALE - MARKETING.xlsx"
  "Doanh thu T11.2025 đến 25.02.xlsx"
  "Data_Dashboard_FINAL_PIPELINE.xlsx"
  "Demo - Phun Xam Vic pipeline.xlsx"
  "output/"
)

echo "======================================================================"
echo " DỌN DỮ LIỆU KHÁCH HÀNG KHỎI GIT"
echo "======================================================================"
echo
echo "Thư mục: $REPO"
echo

# ---------------------------------------------------------------------------
echo "--- BƯỚC 0: Sao lưu trước khi đụng vào lịch sử ---"
BACKUP="../PXV-backup-$(date +%Y%m%d-%H%M%S).bundle"
git bundle create "$BACKUP" --all
echo "Đã sao lưu toàn bộ repo (kể cả lịch sử) vào:"
echo "    $(cd "$(dirname "$BACKUP")" && pwd)/$(basename "$BACKUP")"
echo "Nếu có sự cố, khôi phục bằng: git clone <file .bundle> <thư mục mới>"
echo
read -rp "Enter để tiếp tục, Ctrl+C để dừng... "

# ---------------------------------------------------------------------------
echo
echo "--- BƯỚC 1: Gỡ file dữ liệu khỏi git (file trên ổ đĩa GIỮ NGUYÊN) ---"
for p in "${PII_PATHS[@]}"; do
  if git ls-files --error-unmatch "$p" >/dev/null 2>&1 || \
     [ -n "$(git ls-files "$p" 2>/dev/null)" ]; then
    git rm -r --cached --quiet -- "$p" 2>/dev/null && echo "  gỡ track: $p" || true
  fi
done

CON_LAI=$(git ls-files | grep -icE '\.(csv|xlsx)$' || true)
echo
echo "Số file dữ liệu còn được track: $CON_LAI  (phải là 0)"
if [ "$CON_LAI" != "0" ]; then
  echo "  ⚠️  Còn sót:"
  git ls-files | grep -iE '\.(csv|xlsx)$' | sed 's/^/     /'
  echo "  Thêm chúng vào PII_PATHS trong script rồi chạy lại."
  exit 1
fi

echo
echo "Kiểm tra file trên ổ đĩa vẫn còn (pipeline cần chúng để chạy):"
for f in "kiotviet.csv" "Sales_Marketing dataset - SALE T1-2-3_2026.csv"; do
  [ -f "$f" ] && echo "  ✅ $f" || echo "  ❌ MẤT $f — dừng lại, khôi phục từ bundle!"
done
echo
read -rp "Enter để commit thay đổi này... "

git commit -q -m "Gỡ dữ liệu khách hàng khỏi git

Dữ liệu (tên, SĐT, dịch vụ đã làm) chuyển sang Google Sheets/Drive.
File vẫn nằm trên máy để chạy pipeline, chỉ không còn được git theo dõi.
Lịch sử cũ được dọn riêng ở bước sau."
echo "Đã commit."

# ---------------------------------------------------------------------------
echo
echo "--- BƯỚC 2: Xóa khỏi TOÀN BỘ LỊCH SỬ ---"
echo
echo "Bước này viết lại mọi commit. Cần công cụ git-filter-repo."

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo
  echo "Chưa cài git-filter-repo. Cài bằng một trong các cách:"
  echo "    brew install git-filter-repo"
  echo "    pip3 install git-filter-repo"
  echo
  echo "Cài xong chạy lại script này (bước 1 sẽ tự bỏ qua vì đã xong)."
  exit 0
fi

echo
echo "Sẽ xóa khỏi lịch sử:"
printf '    %s\n' "${PII_PATHS[@]}"
echo
echo "⚠️  Sau bước này, mọi mã commit (hash) sẽ thay đổi."
echo "⚠️  Ai đang có bản clone khác PHẢI clone lại, không được git pull."
echo
read -rp "Gõ 'XOA' để xác nhận: " XACNHAN
[ "$XACNHAN" = "XOA" ] || { echo "Đã hủy."; exit 1; }

ARGS=()
for p in "${PII_PATHS[@]}"; do ARGS+=(--path "$p"); done
git filter-repo --invert-paths "${ARGS[@]}" --force

echo
echo "Đã dọn lịch sử. Kiểm tra:"
SOT=$(git log --all --diff-filter=A --name-only --pretty=format: 2>/dev/null \
      | grep -icE '\.(csv|xlsx)$' || true)
echo "  File dữ liệu còn trong lịch sử: $SOT  (phải là 0)"

# ---------------------------------------------------------------------------
echo
echo "======================================================================"
echo " BƯỚC 3 — BẠN TỰ CHẠY (script không tự làm)"
echo "======================================================================"
echo
echo "git filter-repo đã gỡ remote để tránh push nhầm. Làm tiếp:"
echo
echo "  1. Kiểm tra lịch sử đã sạch:"
echo "       git log --all --name-only --pretty=format: | sort -u | head -30"
echo
echo "  2. Gắn lại remote:"
echo "       git remote add origin https://github.com/tomtran-786/Phun-Xam-Vic---Data-Analysis.git"
echo
echo "  3. Ghi đè lịch sử trên GitHub:"
echo "       git push origin main --force"
echo
echo "  4. Trên GitHub, xóa các bản cache còn sót:"
echo "     - Settings > Branches: xóa branch cũ không dùng"
echo "     - Nếu repo từng có fork: yêu cầu GitHub Support xóa"
echo "       (fork giữ bản sao riêng, force-push không đụng tới được)"
echo
echo "LƯU Ý QUAN TRỌNG:"
echo "  Repo đã từng public, nên dữ liệu có thể đã bị người khác tải về."
echo "  Việc dọn này ngăn rò rỉ TIẾP, không thu hồi được phần đã phát tán."
echo "  Theo Nghị định 13/2023/NĐ-CP, cân nhắc rà soát nghĩa vụ thông báo."
echo
