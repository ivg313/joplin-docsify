# joplin-docsify
Export some tagged Joplin notes to Docsify static site. At least that's the plan.
This is in early development right now.

Based on the joplinexport script written by Stavros Korokithakis: https://gitlab.com/stavros/notes

## Warning
It does not support nested notebooks (subnotebooks) like:
```
Notebook
    SubNotebook
        Note 1
        Note 2
```


## ToDo
- ~~make folder only for public notes~~
- ~~test images/videos/etc export~~
- ~~Rewrite files (and images) export: imho they should be in folder with same name as note or something like that.~~ (kind of impossible, fuck it)
- remake SUMMARY.md generator to _sidebar.md
- See if the hyperlinks from Note to Note are working 
- ...