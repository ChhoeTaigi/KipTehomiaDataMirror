# KipTehomiaDataMirror

Data mirror for ChhoeTaigi KipTehomia. This site provides direct access to the extracted KipTehomia (Taiwanese Place Names) audio and list data. The files are hosted on GitHub Pages for easy access.

## Chu-liāu Pán-koân

版權聲明
- [創用CC姓名標示 3.0 臺灣 授權條款](https://creativecommons.org/licenses/by/3.0/tw/)

![版權聲明](./LICENSE.png)

## Latest Version

You can check [**manifest.json**](./public/manifest.json) for the latest version information programmatically.

## Accessing Files

The files are organized by version. Once updated, the latest files will be in `public/{version}/`.

### 1. Bunji (text data, `bunji/`)

Merged from all 5 source documents into one CSV and one JSON, one row per place name.

* **CSV:** `https://chhoetaigi.github.io/KipTehomiaDataMirror/public/{version}/bunji/KipTehomiaData.csv`
* **JSON:** `https://chhoetaigi.github.io/KipTehomiaDataMirror/public/{version}/bunji/KipTehomiaData.json`
* **Columns:** `來源, 序號, 業者代碼, 國語, 臺灣台語_羅馬字, 臺灣台語_第二羅馬字, 臺灣台語_漢字建議, 臺灣台語_說明, 臺灣客語_羅馬字, 臺灣客語_漢字建議, 臺灣客語_說明, 音檔`
* **`來源` values:** `臺灣鐵路站名`, `捷運站名`, `臺灣高鐵及高鐵快捷公車站名`, `台灣好行旅遊公車站名`, `行政區`, `聚落`, `自然實體`, `公共設施`, `街道`, `增列地名`

### 2. Imtong (audio, `imtong/`)

* **Base URL:** `https://chhoetaigi.github.io/KipTehomiaDataMirror/public/{version}/imtong/`
* **Filename pattern:** `{序號}_{地名}.mp3` — `序號` matches the same column in `bunji/KipTehomiaData.csv`.

## Chu-liāu bāng-chí

地名資料下載
1. [地名清單（placename_list.zip）](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/placename_list.zip)
2. [臺鐵清單（railways_list.zip）](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/railways_list.zip)
3. [高捷清單（tkmrt_list.zip）](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/tkmrt_list.zip)
4. [高鐵清單（thsrc_list.zip）](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/thsrc_list.zip)
5. [台灣好行清單（twtrip_list.zip）](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twtrip_list.zip)

音檔下載 (臺灣台語)
* **行政區:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/administrative_m_mp3.zip)
* **聚落:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/settlement_m_mp3.zip)
* **自然實體:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/naturalentity_m_mp3.zip)
* **公共設施:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/publicutilities_m_mp3.zip)
* **街道:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/street_m_mp3.zip)
* **臺鐵:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/railways_m_mp3.zip)
* **高捷:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/tkmrt_m_mp3.zip)
* **高鐵:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/thsrc_m_mp3.zip)
* **台灣好行:** [mp3](https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twtrip_m_mp3.zip)

## Source

Original data source: 教育部以本土語言標注臺灣地名計畫 <https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/twplacename.html>
