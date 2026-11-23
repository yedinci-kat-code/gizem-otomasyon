# uzun/ — Unfrozen History uzun çizgi video (8-12 dk, 1920x1080, 24 fps)

- Motor: **cizgi-short** — Burak Özer (@burakozerweb), MIT (`engine/`, `tools/`, `vendor/`, `fonts/` kopyası; Zifiri'nin `cizgi/`'sine dokunmaz).
  Eklentiler: yatay boyut (`meta.w/h`), kış şapkaları (`beanie`, `fur`, `hood`) + `scarf`, 24 fps encode ayarları.
- `story.js`: kanal yönetmeni. Soba başındaki yaşlı anlatıcı (host) + 12 kış mekânı:
  cabin, forest, trench, ice (buzda barkentin), camp, pass, frontier, town, harbor, prairie, river, hq.
  Çekimler: host, host_close, wide, character, close, two, run, march, huddle, crowd, object. Yağan kar / tipi otomatik.
- Akış (`.github/workflows/uzun-video.yml`): `scripts/uzun_story.py` (Gemini) → `uzun_voice.py` (Wiro ElevenLabs "Bill",
  yedek edge-tts) → `uzun_build.py` (faster-whisper, düzensiz kesmeler, rüzgâr + tek müzik + efekt) → 16 paralel render
  → `uzun_finish.py` (MP4, QA, SRT, bölümler, YouTube metni). **YouTube'a yükleme yok**: çıktı Artifacts + `uzun-cikti` dalı.
- Konu sırası: `topics.json` (ya da workflow girdisi `topic`).
