#!/bin/zsh
# Back up the iPod's partition map + firmware partition, then flash a new firmware image.
# Run with: sudo zsh tools/backup_and_flash.sh /dev/diskN [expected-current-image] [new-image]
# The installer refuses to write unless the iPod holds exactly expected-current-image.
# Defaults: build/stock/Firmware-25.6.3 (stock 1.3) -> build/Firmware-25.6.3-cjk (tools/build.py)
# Mac-formatted iPods only (partition 2 = firmware, partition 3 = music).
# The music partition (s3) is never read or written.
set -euo pipefail

DISK=${1:?usage: backup_and_flash.sh /dev/diskN [expected-current-image] [new-image]}
RDISK=${DISK/\/dev\/disk//dev/rdisk}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=$ROOT/backups
mkdir -p "$OUT"
BASE=${2:-$ROOT/build/stock/Firmware-25.6.3}
NEW=${3:-$ROOT/build/Firmware-25.6.3-cjk}

diskutil info "${DISK}s2" | grep -q 'Apple_MDFW' || { echo "${DISK}s2 is not an iPod firmware partition (Apple_MDFW); abort"; exit 1; }
[[ -f $BASE && -f $NEW ]] || { echo "missing $BASE or $NEW (run tools/build.py first); abort"; exit 1; }
diskutil info "${DISK}s3" | grep -q 'Volume Name:.*iPod' || { echo "${DISK}s3 volume name has no \"iPod\" in it; abort (rename it in Finder if this really is your iPod)"; exit 1; }

echo "== unmounting $DISK"
diskutil unmountDisk "$DISK"

echo "== backing up partition map (s1) and firmware partition (s2)"
for p in s1 s2; do
  img="$OUT/ipod-${p}-${STAMP}.img"
  dd if="${RDISK}${p}" of="$img" bs=1m 2>/dev/null
  shasum -a 256 "$img" | tee "$img.sha256"
done
cmp <(dd if="${RDISK}s2" bs=1m 2>/dev/null) "$OUT/ipod-s2-${STAMP}.img" && echo "firmware backup verified by re-read"

echo "== dry run"
python3 -I "$ROOT/tools/install_firmware.py" "${RDISK}s2" \
  "$BASE" "$NEW" "$OUT/ipod-osos-${STAMP}.bin"

echo "== writing"
python3 -I "$ROOT/tools/install_firmware.py" "${RDISK}s2" \
  "$BASE" "$NEW" "$OUT/ipod-osos-${STAMP}.bin" --write

chown -R "${SUDO_USER:-$USER}" "$OUT"
diskutil eject "$DISK"
echo "== done. Unplug the iPod and reboot it (hold Menu+Select)."
echo "   To roll back: sudo dd if='$OUT/ipod-s2-${STAMP}.img' of=${RDISK}s2 bs=1m"
