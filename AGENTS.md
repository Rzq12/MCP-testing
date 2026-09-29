# Instruksi agent

- Jawab pertanyaan dalam bahasa Indonesia.
- Untuk angka capaian kinerja, selalu ambil data dari tool MCP `warehouse`.
- Jangan menebak atau menghitung sendiri angka yang tidak ada di hasil tool.
- Di akhir jawaban, sebutkan tool dan tahun data yang dipakai.
- Gunakan `list_unit` untuk daftar unit dan `get_kinerja` untuk capaian kinerja per tahun.
- Gunakan `get_program` untuk daftar program, status, dan anggaran per tahun.
- Gunakan `list_program` untuk daftar nama program yang tersedia.
- Gunakan `get_ringkasan_program` jika pertanyaan membutuhkan gabungan program, kegiatan, anggaran, dan capaian kinerja.
- Gunakan `list_pegawai` untuk daftar seluruh pegawai dari database `sdm`, tanpa menampilkan NIP.
- Gunakan `get_pegawai` untuk daftar pegawai berdasarkan unit dari database `sdm`, tanpa menampilkan NIP.
