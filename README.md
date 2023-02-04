# joplin-docsify
Export some tagged Joplin notes to Docsify static site. At least that's the plan.
This is in early development right now.

Based on the joplinexport script written by Stavros Korokithakis: https://gitlab.com/stavros/notes

## Warning
Nested notebooks or subnotebooks are not supported!
I won't even think about it until Joplin for Android starts supporting them.
So this tree will not work properly:
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
- ~~remake SUMMARY.md generator to _sidebar.md~~ 
- ~~See if the hyperlinks from Note to Note are working~~
- Figure out how to generate README.md (home page)
- Decide how and where to display the last changed information
- ...