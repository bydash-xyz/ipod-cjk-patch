# iPod CJK Patch

**純正ファームウェア 1.3 の iPod Video 5G/5.5G で、中国語・日本語・韓国語をきれいに表示。**

[English](README.md) | [简体中文](README.zh-CN.md) | **日本語** | [한국어](README.ko.md)

Apple 純正ファームウェア **1.3**（`iPod_25.1.3.ipsw`）の **iPod Video 5G/5.5G** で、中国語・日本語・
韓国語をきれいに表示できるようにします。Rockbox ではありません。Apple のファームウェアはそのまま動作し、
変わるのはフォントだけです。iPod 内の音楽は消えません。

純正ファームウェアでは、CJK の歌詞が 4 種類のビットマップフォントを混ぜて表示します。そのため文字が
1〜2 ピクセル上下にずれ、行の途中で書体が変わり、一部の文字（啰、嘢、哋 など）は表示されません。
同じ行の英字や記号は、さらに別の太いアンチエイリアスのフォントで表示されます。
メニュー（曲名・アーティスト名・アルバム名）でも、簡体字の多く（泷、犸 など）が欠けています。

![純正と修正後の比較：各ファームウェア自身のフォントで描画したメニューと歌詞](docs/before-after.png)

<sub>`tools/render_preview.py` が各ファームウェアのフォントデータから描画したものです（3 倍拡大）。
純正側では、Podium Sans 16 にある文字はそれを、ない文字はファームウェアのフォント登録順で最初にその文字を
持つ 12px フォントを使っています。実機の CJK の検索順は少し異なりますが、フォントが混在する様子は同じです。</sub>

> **自己責任でご利用ください。** このツールは iPod のファームウェアパーティションに書き込みます。
> 書き込みスクリプトは可能な限りのチェックを行い、事前にバックアップを取ります。Finder/iTunes で
> 復元すれば iPod は必ず元に戻せますが、その場合は音楽が消去されます。

## 変更内容

- **歌詞（OS イメージに組み込まれた 12px ビットマップフォント）。** すべての CJK 文字（約 1.95 万字：
  漢字、かな、ハングル、CJK 記号、全角文字）を [Fusion Pixel 12px](https://github.com/TakWolf/fusion-pixel-font)
  （OFL）で描き直し、同じセルと同じベースラインにそろえました。各文字はひとつのフォントにしか存在しない
  ため、ファームウェアのフォントフォールバック順は影響しなくなります。簡体字は zh_hans、繁体字は zh_hant、
  日本語固有の漢字とかなは ja、ハングルは ko のグリフを使います。純正で欠けていた文字を追加し、康熙部首の
  似た文字（⼀ ⼩ ⾸ ⻋）は通常の文字に割り当てています。
- **歌詞の英字と記号（Podium Sans 16、これも OS イメージ内）。** 歌詞は CJK 以外の文字をすべてこの太い
  アンチエイリアスのフォントで表示するため、英単語や括弧、引用符が隣の CJK 文字より太く見えていました。
  そのグリフを Fusion Pixel 12px のプロポーショナル版で描き直し、CJK と同じベースラインにそろえました。
  純正では CJK フォントにしかない記号（♪ ★ ① → ※、罫線など）もこのフォントに移し、記号ごとに書体を
  ひとつにしています。Fusion Pixel にない文字（ベトナム語などのまれなアクセント付き文字、Apple の私用
  アイコン）は純正のグリフのままです。歌詞画面以外で Podium Sans 16 が使われている場合、そこの文字も
  同じように変わります。
- **メニュー / 再生中画面（リソースボリューム内の `CJK.ttf`、18px 4 ビット）。** 630 グリフを追加しました。
  GB2312 で欠けていた文字すべてと、`charsets/menu.txt` の文字です。既存のヒラギノのグリフに合わせ、
  ヒラギノ角ゴ 簡体中文 W6（Hiragino Sans GB）からラスタライズしています。

## 必要なもの

- ファームウェア 1.3 の iPod Video 5G または 5.5G（5.5G で動作確認済み）、**Mac フォーマット**
  （Windows/FAT32 フォーマットの iPod はパーティション構成が異なり、書き込みスクリプトは対応していません）
- macOS：メニューフォントにはシステムの Hiragino Sans GB を、書き込みには `diskutil` を使います
- [uv](https://docs.astral.sh/uv/)（または Python 3.11 以上と `fonttools`、`pillow`、`mutagen`）
- 初回ビルド時のインターネット接続：純正の `iPod_25.1.3.ipsw` を Apple のサーバーからダウンロードします
  （Apple のファームウェアは著作物のため、このリポジトリには含まれていません）

## ビルド

```bash
uv run python -I tools/build.py
```

`iPod_25.1.3.ipsw` を Apple から `build/` にダウンロードし、既知の SHA1
（`0f2dd984c5d56475bdf3c14b4bc7541b799f2c85`）と SHA256 で検証します。Apple はこのファイルを平文の HTTP
でしか配布していないため、安全性はハッシュ検証で担保しています。IPSW をすでに持っている場合は
`--ipsw path/to/iPod_25.1.3.ipsw` を指定するとダウンロードを省略できます。

歌詞のグリフは、GitHub で公開されている Fusion Pixel 12px の BDF リリース（v2026.09.25）から取得します。
ビルド時にこれとプロポーショナル版（英字と記号用）もダウンロードし、固定の SHA256 で検証して `build/` に
キャッシュします。

ビルドすると `build/Firmware-25.6.3-cjk`、純正のベース `build/stock/Firmware-25.6.3`、
`build/before-after.png` が生成されます。ビルドは決定的で、出力がリリース版と一致するかどうかを
スクリプトが表示します（SHA256 `bf83fc2e3c38ba82da93f4f058783bfe9ef38899f6eb6dbf93fae567239b97e8`）。

## 書き込み（音楽は残ります）

1. iPod を接続し、ディスクとして使用を有効にします（またはディスクモードにします：Menu+Select を押し続けて
   リセットし、続けて Select+Play を押し続けます）。
2. `diskutil list` でディスク番号を確認します。iPod の `diskNs2` が `Apple_MDFW` パーティションです。
3. 実行します：

```bash
sudo zsh tools/backup_and_flash.sh /dev/diskN
```

スクリプトはパーティションマップとファームウェアパーティションを `backups/` にバックアップします。
iPod の現在のファームウェアが `build/stock/Firmware-25.6.3` とバイト単位で一致しない限り、書き込みません。
ドライランを行い、変更があるセクタだけを書き込み、読み戻して検証してから iPod を取り出します。その後、
iPod を再起動してください（Menu+Select を押し続けます）。

純正ではなく以前のビルドの上に書き込む場合は、iPod の現在のイメージと新しいイメージを指定します：
`backup_and_flash.sh /dev/diskN <現在のイメージ> <新しいイメージ>`。

## 元に戻す

スクリプトが作成したファームウェアパーティションのバックアップを書き戻します（iPod が起動しない場合は
ディスクモードにしてください）：

```bash
sudo dd if=backups/ipod-s2-YYYYMMDD-HHMMSS.img of=/dev/rdiskNs2 bs=1m
```

Finder/iTunes で復元しても戻せますが、音楽は消去されます。

## 文字の追加

`charsets/lyrics_extra.txt`（歌詞）または `charsets/menu.txt`（メニュー）に文字を追記して再ビルドします。
`lyrics_extra.txt` の CJK 以外の記号（♫ など）は Podium Sans 16 に追加されます。
ライブラリで使われているのにファームウェアがうまく表示できない文字を調べるには：

```bash
uv run python -I tools/scan_library.py ~/Music/your-library build/Firmware-25.6.3-cjk report.json
```

どの 12px フォントにもない文字、複数のフォントにある文字（純正でベースラインがずれる原因）、
曲名・アーティスト名・アルバム名で `CJK.ttf` に欠けている文字を報告します。

`tools/make_test_track.py` は、短い無音の `.m4a` に、すべてのケースを確認できる曲名・アーティスト名・
アルバム名・歌詞を書き込みます。ライブラリに追加して、iPod で表示を確認してください。

## ツール

| ファイル | 用途 |
|---|---|
| `tools/build.py` | ワンステップビルド：IPSW のダウンロードと検証、ビルド、比較画像の描画 |
| `tools/build_unified.py` | `osos` イメージ内の 12px CJK ビットマップフォントを再構築 |
| `tools/build_latin.py` | Podium Sans 16（歌詞の英字と記号）を Fusion Pixel で描き直す |
| `tools/extend_cjk_ttf.py` | `CJK.ttf` の 18px EBDT ストライクにグリフを追加 |
| `tools/build_rsrc.py` | `rsrc` FAT ボリューム内のファイルを置き換え、チェックサムを修正 |
| `tools/install_firmware.py` | デバイスのファームウェアパーティションをその場でパッチ（標準ライブラリのみ） |
| `tools/backup_and_flash.sh` | バックアップ + 安全チェック + `install_firmware.py` |
| `tools/scan_library.py` | ファームウェアがうまく表示できないライブラリ内の文字を報告 |
| `tools/render_preview.py` | 2 つのファームウェアのフォントで文字を並べて描画（`docs/before-after.png`） |
| `tools/pixofont.py` | ファームウェアのビットマップフォントの読み書き；`pixofont.py <fw>` で一覧表示 |
| `tools/fat16.py`、`ipodfw.py`、`bdf.py`、`hiragino_raster.py` | 補助的な読み書きモジュール |

## ファームウェアのメモ（ハマったところ）

- IPSW ファイルでは、各イメージのデータはディレクトリの `devOffset + 0x800` から始まります（`rsrc` は
  さらに `entryOffset` を加算）。デバイス上では `devOffset + 0x200` からです。チェックサムはイメージ全体の
  バイトの 32 ビット和です。
- `rsrc` ボリュームは「FAT16」と表示されていますが、実際は FAT12 です。
- **12px 固定幅フォントのグリフ帯の幅は 32767 ピクセル以下でなければなりません**（グリフの x 座標が符号付き
  16 ビットのため）。超えると、それ以降のグリフがすべて空白になります。Apple 純正の最大は 31836 ピクセル
  で、`build_unified.py` はこれを上限にしています。1 フォントあたり約 2,400 グリフです。
- ファームウェアのフォントフォールバック順に頼らないでください。フォント登録順どおりではありません。
  各文字はひとつのフォントからだけ供給するようにします。
- 歌詞はまず Podium Sans 16 で表示され、そこにない文字だけが 12px フォントにフォールバックします。同じ行の
  異なるフォントのグリフは、宣言されたアセントではなくセルの下端でそろえられます（写真から測定：Podium
  Sans 16 の高さ 13 ピクセルの括弧が CJK 文字と同じ行で終わる）。
- ビットマップフォントの形式は iPodWizard の `Font.h` に基づいています。

## 協力募集：ほかの iPod とファームウェアへの対応

現時点で動作確認できているのは、**ファームウェア 1.3・Mac フォーマットの iPod Video 5.5G** 1 台だけです。
ほかの機種をお持ちなら、より多くの人が使えるようにする手助けをお願いします：

- **動作報告：** ファームウェア 1.3 の 5G（30/60GB）や、Windows フォーマットの iPod。うまくいく点・いかない
  点を、できれば写真付きで教えてください。
- **ほかのファームウェア：** 1.2.x 以前の 5G 用ファームウェアは内部の配置が異なる可能性があります。
- **ほかの機種：** nano や classic は別のファームウェア形式かもしれません。フォントの格納方法を調べるだけでも、
  有益な第一歩になります。

[CONTRIBUTING.md](CONTRIBUTING.md#porting-to-another-ipod-or-firmware)（英語）に、この機種・バージョンに依存
している箇所をまとめています。移植報告用の issue テンプレートもあります。

## 謝辞

- 歌詞のグリフは TakWolf 氏の [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font)（OFL 1.1）を
  使用しています。これは [Ark Pixel](https://github.com/TakWolf/ark-pixel-font)、
  [Cubic 11](https://github.com/ACh-K/Cubic-11)、[Galmuri](https://github.com/quiple/galmuri) を基にしています。
- [iPodWizard](https://sourceforge.net/projects/ipodwizard/)：その `Font.h` がファームウェアのビットマップ
  フォント形式を記述しており、`tools/pixofont.py` はそれに従っています。
- メニューのグリフは、お使いの Mac 上でシステムフォント Hiragino Sans GB からラスタライズされます。
  このリポジトリに Hiragino のデータは含まれていません。
- [fontTools](https://github.com/fonttools/fonttools)、[Pillow](https://python-pillow.org/)、
  [mutagen](https://github.com/quodlibet/mutagen) を使用しています。

iPod は Apple Inc. の商標です。このプロジェクトは Apple と提携しておらず、Apple の承認も受けていません。

## ライセンス

コードは MIT ライセンスです（`LICENSE` を参照）。Fusion Pixel は SIL Open Font License 1.1 で、
ライセンス文と入手元の情報は `third_party/fusion-pixel/` にあります。このリポジトリにはフォントファイル、
Apple のファームウェア、Apple のフォントは含まれていません。ビルド時に Apple の IPSW と Fusion Pixel の
リリースをダウンロードし、ローカルでファームウェアにパッチを当てます。`build/` は git の対象外です。
ビルドしたファームウェアイメージは公開しないでください。
