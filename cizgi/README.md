# cizgi/ — Zifiri Saatler çizgi film motoru

- `engine/`, `tools/`, `vendor/`, `fonts/`: **cizgi-short** kiti — Burak Özer (@burakozerweb), MIT.
  Eklentiler: `engine/cast.js` içine fener (`lantern`) objesi, `tools/render.py` içine `--query`.
- `story.js`: Zifiri Saatler yönetmeni. Her video için kod yazılmaz; `work/plan.json` içindeki
  çekim planını (Gemini üretir) okur ve 13 hazır mekân + sabit maskot **Zifiri Bekçi** ile canlandırır.
- Çekim süreleri sabit değildir: her çekim seslendirmedeki cümlesi kadar sürer, uzun cümleler
  seslendirmedeki duraklardan (virgül/nokta) bölünür (`scripts/cizgi_build.py`).

Mekânlar: kosk_ic, kosk_dis, mezarlik, koy, kopru, kale, saray, magara, carsi, orman, sahil, avlu, arsiv
Çekimler: bekci_hook, bekci, genis, karakter, yakin, ikili, kovalamaca, kalabalik, obje, gercek, bekci_kapanis
