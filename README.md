# joplin-docsify
Export some tagged Joplin notes to Docsify static site. At least that's the plan.
This is in early development right now.

Based on the joplinexport script written by Stavros Korokithakis: https://gitlab.com/stavros/notes

## Warning
Nested notebooks or sub-notebooks are not supported!
I won't even think about it until Joplin for Android starts supporting them.
So this tree will not work properly:
```
Notebook
    SubNotebook
        Note 1
        Note 2
```


## ToDo
- [x] Make folder only for public notes
- [x] Test images/videos/etc export
- [x] Rewrite files (and images) export: imho they should be in folder with same name as note or something like that. (kind of impossible, fuck it)
- [x] Remake SUMMARY.md generator to _sidebar.md
- [x] See if the hyperlinks from Note to Note are working
- [x] Decide how and where to display the last changed information
- [x] Figure out how to generate README.md (home page)
- [x] Docsify index.html generator with args control
- [ ] ...