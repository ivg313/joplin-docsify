# joplin-docsify
Export some tagged Joplin notes to Docsify static site. At least that's the plan.
This is in early development right now.

Based on the joplinexport script written by Stavros Korokithakis: https://gitlab.com/stavros/notes

## ToDo
- [x] Make folder only for public notes
- [x] Test images/videos/etc export
- [x] Rewrite files (and images) export: imho they should be in folder with same name as note or something like that. (kind of impossible, fuck it)
- [x] Remake SUMMARY.md generator to _sidebar.md
- [x] See if the hyperlinks from Note to Note are working
- [x] Decide how and where to display the last changed information
- [x] Figure out how to generate README.md (home page)
- [x] Docsify index.html generator with args control
- [x] Kind of "News" on homepage
- [x] Figure out how I want to sort folders, articles in folders and implement this (i'm to lazy and stupid to do this)
- [x] Move from "updated" to "created" datetime
- [x] Rebuild only if Joplin database changed
- [x] Try to implement sub-notebooks aka nested folders (kinda, it's look great but messy inside)
- [ ] Implement excerpt for news (latest pages list) on homepage. Should "news" have datetime?
- [ ] Try to implement RSS
- [x] Implement (or steal from Stavros) icons export
- [x] Some kind of translation needed for hardcoded words like "created" and "updated". (i have zero fucks about people who don't understand english, so fuck it)
- [ ] Implement hidden pages (kinda work, need more tests)
- [ ] ...