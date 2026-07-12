# Zifiri Saatler — Otomatik Video Uretim Sistemi

Bu repo, YouTube Shorts icin gizem/korku hikayelerini tamamen otomatik
uretip yayinlayan bir sistemdir.

## Nasil calisir

Her tetiklendiginde (gunde 3 kez, otomatik):

1. **Gemini API** ile ozgun bir gizem/korku hikayesi ve basligi uretilir
2. **edge-tts** (ucretsiz) ile Turkce seslendirme yapilir, kelime kelime zamanlama cikarilir
3. **Pexels API** ile rastgele, telifsiz bir arkaplan videosu cekilir
4. **ffmpeg** ile ust panelde hikaye+altyazi, alt panelde arkaplan video birlestirilir
5. **YouTube Data API** ile video otomatik olarak kanala yuklenir

## Zamanlama

`.github/workflows/daily-upload.yml` icinde tanimli, gunde 3 kez (yaklasik
09:00, 15:00, 20:00 TR saati) otomatik calisir.

Elle test etmek icin: repo'da **Actions** sekmesi -> **"Zifiri Saatler - Otomatik
Video Uretimi"** -> sag ustten **"Run workflow"** butonuna tikla.

## Gerekli Secrets (Settings -> Secrets and variables -> Actions)

- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

## Hata ayiklama

Her calistirmadan sonra, uretilen ara dosyalar (senaryo, ses, video) 3 gun
boyunca **Actions -> [calistirma] -> Artifacts** bolumunde indirilebilir.
Bir sorun oldugunda once oradaki `story.json` ve `final.mp4` dosyalarina
bakmak en hizli teshis yontemidir.

## Hacmi degistirmek

`daily-upload.yml` icindeki `cron` satirlarina yeni saatler ekleyip/cikararak
gunluk video sayisi ayarlanabilir.
