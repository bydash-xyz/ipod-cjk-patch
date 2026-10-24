# iPod CJK Patch

**순정 펌웨어 1.3의 iPod Video 5G/5.5G에서 중국어·일본어·한국어를 깔끔하게.**

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어**

Apple 순정 펌웨어 **1.3**(`iPod_25.1.3.ipsw`)을 쓰는 **iPod Video 5G/5.5G**에서 중국어, 일본어, 한국어가
깔끔하게 표시되도록 합니다. Rockbox가 아닙니다. Apple 펌웨어는 그대로 동작하고 글꼴만 바뀝니다. iPod에
있는 음악도 그대로 남습니다.

순정 펌웨어는 CJK 가사를 네 가지 비트맵 글꼴을 섞어서 표시합니다. 그래서 글자가 1–2픽셀씩 위아래로
들쭉날쭉하고, 한 줄 안에서 글꼴 모양이 바뀌며, 일부 글자(啰, 嘢, 哋 등)는 아예 표시되지 않습니다. 같은 줄의 영문자와
기호는 또 다른 굵은 안티앨리어싱 글꼴로 표시됩니다. 메뉴
(곡명, 아티스트, 앨범 이름)에서도 간체자 상당수(泷, 犸 등)가 빠져 있습니다.

![순정과 수정 후 비교: 각 펌웨어의 자체 글꼴로 렌더링한 메뉴와 가사](docs/before-after.png)

<sub>`tools/render_preview.py`가 각 펌웨어의 글꼴 데이터로 렌더링한 이미지입니다(3배 확대). 순정 쪽은
Podium Sans 16에 있는 글자는 그 글꼴을, 없는 글자는 펌웨어 글꼴 등록 순서에서 해당 글자를 가진 첫 번째
12px 글꼴을 사용합니다. 실제 기기의 CJK 검색 순서는 조금 다르지만, 글꼴이 섞이는 양상은 같습니다.</sub>

> **사용에 따른 책임은 본인에게 있습니다.** 이 도구는 iPod의 펌웨어 파티션에 씁니다. 쓰기 스크립트는
> 가능한 모든 검사를 하고 먼저 백업을 만듭니다. Finder/iTunes로 복원하면 iPod는 언제나 되살릴 수 있지만,
> 음악이 지워집니다.

## 바뀌는 내용

- **가사 (OS 이미지에 컴파일된 12px 비트맵 글꼴).** 모든 CJK 문자(약 1만 9,500자: 한자, 가나, 한글, CJK
  문장 부호, 전각 문자)를 [Fusion Pixel 12px](https://github.com/TakWolf/fusion-pixel-font)(OFL)로 다시
  그려, 같은 셀과 같은 기준선을 쓰게 했습니다. 각 글자는 하나의 글꼴에만 있으므로 펌웨어의 글꼴 대체 순서가
  더 이상 영향을 주지 않습니다. 간체자는 zh_hans, 번체자는 zh_hant, 일본어 전용 한자와 가나는 ja, 한글은
  ko 글리프를 씁니다. 순정에 없던 글자를 추가했고, 강희 부수 모양 글자(⼀ ⼩ ⾸ ⻋)는 일반 글자로
  연결했습니다.
- **가사의 영문자와 기호 (Podium Sans 16, 역시 OS 이미지 안).** 가사는 CJK가 아닌 글자를 모두 이 굵은
  안티앨리어싱 글꼴로 표시하므로, 영어 단어와 괄호, 따옴표가 옆의 CJK 글자보다 굵어 보였습니다. 이 글꼴의
  글리프를 Fusion Pixel 12px 비례폭 버전으로 다시 그려 CJK와 같은 기준선에 맞췄습니다. 순정에서는 CJK
  글꼴에만 있던 기호(♪ ★ ① → ※, 괘선 등)도 이 글꼴로 옮겨 기호마다 모양이 하나가 되게 했습니다. Fusion
  Pixel에 없는 글자(베트남어 등 드문 악센트 글자, Apple 전용 아이콘)는 순정 글리프를 그대로 씁니다. 가사
  화면 밖에서 Podium Sans 16을 쓰는 곳이 있다면 그곳의 글자도 똑같이 바뀝니다.
- **메뉴 / 재생 화면 (리소스 볼륨의 `CJK.ttf`, 18px 4비트).** 글리프 630개를 추가했습니다. GB2312에서
  빠져 있던 글자 전부와 `charsets/menu.txt`의 글자입니다. 기존 Hiragino 글리프와 맞도록 Hiragino Sans GB
  W6에서 래스터화했습니다.

## 요구 사항

- 펌웨어 1.3의 iPod Video 5G 또는 5.5G(5.5G에서 테스트), **Mac 포맷**(Windows/FAT32 포맷 iPod는 파티션
  구조가 달라 쓰기 스크립트가 지원하지 않습니다)
- macOS: 메뉴 글꼴에 시스템의 Hiragino Sans GB를, 쓰기에 `diskutil`을 사용합니다
- [uv](https://docs.astral.sh/uv/)(또는 Python 3.11 이상과 `fonttools`, `pillow`, `mutagen`)
- 첫 빌드 시 인터넷 연결: 순정 `iPod_25.1.3.ipsw`를 Apple 서버에서 내려받습니다(Apple 펌웨어는 저작권이
  있어 이 저장소에 포함되지 않습니다)

## 빌드

```bash
uv run python -I tools/build.py
```

`iPod_25.1.3.ipsw`를 Apple에서 `build/`로 내려받고, 알려진 SHA1
(`0f2dd984c5d56475bdf3c14b4bc7541b799f2c85`)과 SHA256으로 검증합니다. Apple은 이 파일을 암호화되지 않은
HTTP로만 제공하므로, 안전성은 해시 검증으로 보장합니다. IPSW가 이미 있다면
`--ipsw path/to/iPod_25.1.3.ipsw`로 다운로드를 건너뛸 수 있습니다.

가사 글리프는 GitHub에 공개된 Fusion Pixel 12px BDF 릴리스(v2026.09.25)에서 가져옵니다. 빌드할 때 이
파일과 비례폭 버전(영문자와 기호용)도 내려받아 고정된 SHA256으로 검증하고 `build/`에 캐시합니다.

빌드하면 `build/Firmware-25.6.3-cjk`, 순정 기준 이미지 `build/stock/Firmware-25.6.3`,
`build/before-after.png`가 만들어집니다. 빌드는 결정적이며, 결과가 배포 빌드와 같은지 스크립트가
알려 줍니다(SHA256 `bf83fc2e3c38ba82da93f4f058783bfe9ef38899f6eb6dbf93fae567239b97e8`).

## 펌웨어 쓰기 (음악 유지)

1. iPod를 연결하고 디스크로 사용을 켭니다(또는 디스크 모드로 들어갑니다: Menu+Select를 길게 눌러
   재시작한 뒤 Select+Play를 길게 누릅니다).
2. `diskutil list`로 디스크 번호를 확인합니다. iPod의 `diskNs2`가 `Apple_MDFW` 파티션입니다.
3. 실행합니다:

```bash
sudo zsh tools/backup_and_flash.sh /dev/diskN
```

스크립트는 파티션 맵과 펌웨어 파티션을 `backups/`에 백업합니다. iPod의 현재 펌웨어가
`build/stock/Firmware-25.6.3`과 바이트 단위로 일치하지 않으면 쓰지 않습니다. 시험 실행을 한 뒤, 바뀌는
섹터만 쓰고, 다시 읽어 검증하고, iPod를 추출합니다. 그다음 iPod를 재시작하세요(Menu+Select를 길게 누름).

순정이 아니라 이전 빌드 위에 쓰려면, iPod에 지금 있는 이미지와 새 이미지를 지정합니다:
`backup_and_flash.sh /dev/diskN <현재 이미지> <새 이미지>`.

## 되돌리기

스크립트가 만든 펌웨어 파티션 백업을 다시 씁니다(iPod가 부팅되지 않으면 디스크 모드로 들어가세요):

```bash
sudo dd if=backups/ipod-s2-YYYYMMDD-HHMMSS.img of=/dev/rdiskNs2 bs=1m
```

Finder/iTunes로 복원해도 되지만, 음악이 지워집니다.

## 글자 추가

`charsets/lyrics_extra.txt`(가사) 또는 `charsets/menu.txt`(메뉴)에 글자를 추가하고 다시 빌드합니다.
`lyrics_extra.txt`에 넣은 CJK가 아닌 기호(♫ 등)는 Podium Sans 16에 추가됩니다.
라이브러리에 쓰였지만 펌웨어가 제대로 표시하지 못하는 글자를 찾으려면:

```bash
uv run python -I tools/scan_library.py ~/Music/your-library build/Firmware-25.6.3-cjk report.json
```

어느 12px 글꼴에도 없는 글자, 여러 글꼴에 있는 글자(순정에서 기준선이 흔들리는 원인), 곡명·아티스트·
앨범에 쓰였지만 `CJK.ttf`에 없는 글자를 보고합니다.

`tools/make_test_track.py`는 짧은 무음 `.m4a`에 모든 경우를 확인할 수 있는 곡명, 아티스트, 앨범, 가사를
기록합니다. 라이브러리에 추가한 뒤 iPod에서 확인하세요.

## 도구

| 파일 | 용도 |
|---|---|
| `tools/build.py` | 원스텝 빌드: IPSW 다운로드·검증, 빌드, 비교 이미지 렌더링 |
| `tools/build_unified.py` | `osos` 이미지의 12px CJK 비트맵 글꼴 재구성 |
| `tools/build_latin.py` | Podium Sans 16(가사의 영문자와 기호)을 Fusion Pixel로 다시 그림 |
| `tools/extend_cjk_ttf.py` | `CJK.ttf`의 18px EBDT 스트라이크에 글리프 추가 |
| `tools/build_rsrc.py` | `rsrc` FAT 볼륨의 파일을 교체하고 체크섬 수정 |
| `tools/install_firmware.py` | 기기의 펌웨어 파티션을 제자리에서 패치(표준 라이브러리만 사용) |
| `tools/backup_and_flash.sh` | 백업 + 안전 검사 + `install_firmware.py` |
| `tools/scan_library.py` | 펌웨어가 제대로 표시하지 못하는 라이브러리 글자 보고 |
| `tools/render_preview.py` | 두 펌웨어의 글꼴로 글자를 나란히 렌더링(`docs/before-after.png`) |
| `tools/pixofont.py` | 펌웨어 비트맵 글꼴 읽기/쓰기; `pixofont.py <fw>`로 목록 표시 |
| `tools/fat16.py`, `ipodfw.py`, `bdf.py`, `hiragino_raster.py` | 보조 읽기/쓰기 모듈 |

## 펌웨어 메모 (고생한 부분)

- IPSW 파일에서 각 이미지의 데이터는 디렉터리의 `devOffset + 0x800`에서 시작합니다(`rsrc`는
  `entryOffset`을 더함). 기기에서는 `devOffset + 0x200`에서 시작합니다. 체크섬은 이미지 전체 바이트의
  32비트 합입니다.
- `rsrc` 볼륨은 "FAT16"이라고 표시되어 있지만 실제로는 FAT12입니다.
- **12px 고정폭 글꼴의 글리프 띠 너비는 32767픽셀 이하여야 합니다**(글리프 x 좌표가 부호 있는 16비트).
  넘으면 그 뒤의 글리프가 모두 빈칸으로 나옵니다. Apple 순정의 최댓값은 31836픽셀이며,
  `build_unified.py`는 이를 상한으로 씁니다. 글꼴 하나에 약 2,400개 글리프입니다.
- 펌웨어의 글꼴 대체 순서에 의존하지 마세요. 글꼴 등록 순서를 따르지 않습니다. 각 글자는 하나의 글꼴에서만
  오도록 하세요.
- 가사는 먼저 Podium Sans 16으로 표시하고, 거기에 없는 글자만 12px 글꼴로 대체합니다. 한 줄에 섞인 서로
  다른 글꼴의 글리프는 선언된 어센트가 아니라 셀의 아래쪽 끝을 기준으로 정렬됩니다(사진으로 측정: Podium
  Sans 16의 13픽셀 높이 괄호가 CJK 글자와 같은 줄에서 끝남).
- 비트맵 글꼴 형식은 iPodWizard의 `Font.h`를 따릅니다.

## 도움 요청: 더 많은 iPod와 펌웨어 버전 지원

지금까지는 **펌웨어 1.3, Mac 포맷의 iPod Video 5.5G** 한 대에서만 테스트했습니다. 다른 기기가 있다면 더 많은
사람이 쓸 수 있도록 도와주세요:

- **테스트 보고:** 펌웨어 1.3의 5G(30/60GB)나 Windows 포맷 iPod. 무엇이 되고 안 되는지, 가능하면 사진과
  함께 알려 주세요.
- **다른 펌웨어 버전:** 1.2.x 이전의 5G 펌웨어는 내부 배치가 다를 수 있습니다.
- **다른 기종:** nano와 classic은 다른 펌웨어 형식을 쓸 수 있습니다. 글꼴이 어떻게 저장되는지 분석하는 것만으로도
  좋은 출발점이 됩니다.

[CONTRIBUTING.md](CONTRIBUTING.md#porting-to-another-ipod-or-firmware)(영어)에 이 기종과 버전에 묶여 있는
부분을 정리해 두었고, 포팅 보고용 issue 템플릿도 있습니다.

## 감사의 말

- 가사 글리프는 TakWolf의 [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font)(OFL 1.1)를
  사용합니다. 이 글꼴은 [Ark Pixel](https://github.com/TakWolf/ark-pixel-font),
  [Cubic 11](https://github.com/ACh-K/Cubic-11), [Galmuri](https://github.com/quiple/galmuri)를 바탕으로 합니다.
- [iPodWizard](https://sourceforge.net/projects/ipodwizard/): `Font.h`에 펌웨어 비트맵 글꼴 형식이 정리되어
  있으며, `tools/pixofont.py`는 이를 따릅니다.
- 메뉴 글리프는 사용자의 Mac에서 시스템 글꼴 Hiragino Sans GB로 래스터화됩니다. 이 저장소에는 Hiragino
  데이터가 없습니다.
- [fontTools](https://github.com/fonttools/fonttools), [Pillow](https://python-pillow.org/),
  [mutagen](https://github.com/quodlibet/mutagen)을 사용합니다.

iPod는 Apple Inc.의 상표입니다. 이 프로젝트는 Apple과 제휴하지 않았으며 Apple의 승인을 받지 않았습니다.

## 라이선스

코드는 MIT 라이선스입니다(`LICENSE` 참고). Fusion Pixel은 SIL Open Font License 1.1을 따르며, 라이선스
전문과 출처 정보는 `third_party/fusion-pixel/`에 있습니다. 이 저장소에는 글꼴 파일, Apple 펌웨어, Apple
글꼴이 포함되어 있지 않습니다. 빌드할 때 Apple의 IPSW와 Fusion Pixel 릴리스를 내려받아 로컬에서 펌웨어를
패치하며, `build/`는 git에서 제외됩니다. 빌드한 펌웨어 이미지를 공개하지 마세요.
