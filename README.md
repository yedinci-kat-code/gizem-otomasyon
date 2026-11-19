# Zifiri Saatler — Otomatik Video Uretim Sistemi

Bu repo, YouTube Shorts icin gizem/korku hikayelerini tamamen otomatik
uretip yayinlayan bir sistemdir.

## Nasil calisir (v3: Zifiri Bekci cizgi film Short)

Her tetiklendiginde:

1. **Gemini** efsane -> gercek formatinda senaryo + **cekim plani** yazar (beats: cumle, cekim,
   mekan, karakterler, duygu, efekt). Sabit maskot anlatici **Zifiri Bekci** videoyu acar, arada
   izleyiciye doner, gercegi parsomenle aciklar ve acilis karesine donerek kapatir (loop).
2. **edge-tts** (ucretsiz) Turkce seslendirir, kelime kelime zamanlama cikarir.
3. `scripts/cizgi_build.py` her cekimi **seslendirmesi kadar** surdurur (sabit sure yok; uzun
   cumleler seslendirmedeki duraklardan bolunur), kesintisiz gizem muzigi + efektleri kodla uretir.
4. `cizgi/` motoru (cizgi-short, MIT - Burak Ozer) kareleri **4 paralel GitHub isinde** render eder.
5. `scripts/cizgi_finish.py` MP4'u birlestirir, eksik/siyah kare kontrolu yapar, yazisiz kapak cikarir.
6. **YouTube Data API** ile yuklenir. Elle calistirirken `upload=false` secersen video sadece
   Artifacts'a duser, yayina girmez.

## Zamanlama

`.github/workflows/daily-upload.yml` icinde tanimli, gunde 3 kez (yaklasik
09:00, 15:00, 20:00 TR saati) otomatik calisir.

Elle test etmek icin: repo'da **Actions** sekmesi -> **"Zifiri Saatler - Otomatik
Video Uretimi"** -> sag ustten **"Run workflow"** butonuna tikla.

## Gerekli Secrets (Settings -> Secrets and variables -> Actions)

- `GEMINI_API_KEY`
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
