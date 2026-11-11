# houses/

Your houses go here, and they never go into the shared toolkit repo (it ignores everything in
this folder except this file). Claude sets it up on first run ("set me up"): a private repo of
your own, with a folder per house (`<house>/house.md`) and a folder per room
(`<house>/rooms/<room>/`). The home page lists them by itself (the server's database, which also
keeps their names and card lines: back up `data/home-render.db` too). Push it to a private remote if
you want a backup.
