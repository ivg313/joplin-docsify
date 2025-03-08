import dataclasses
import mimetypes
import re
import sqlite3
import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from shutil import copy
from shutil import rmtree
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union

parser = argparse.ArgumentParser(description='Some config...')
parser.add_argument('-j', '--joplin', default=Path.home() /
                                              '.config/joplin-desktop', help="Path to Joplin directory.")
parser.add_argument('-d', '--docsify', default='docsify',
                    help="Path to Docsify directory.")
parser.add_argument('-t', '--theme', default='vue',
                    help='Docsify theme, default is "vue", alternatives: "buble", "dark" and "pure"')
parser.add_argument('-n', '--name', default='My Notes',
                    help='Name of your site (in double quotes).')
parser.add_argument('-s', '--save-index', action='store_true',
                    help='Do not overwrite index.html')
parser.add_argument('-l', '--disable-latest', action='store_true',
                    help='Do not list latest notes on homepage')
parser.add_argument('-f', '--force', action='store_true',
                    help='Force rebuilding even if nothing changes')
parser.add_argument('-c', '--disable-cdn', action='store_true',
                    help='Instead of CDN, use a local copy of Docsify')
parser.add_argument('-b', '--blog', default='Blog',
                    help='Blog folder name, default is "Blog"')
args = parser.parse_args()


def slugify(text):
    """Convert `text` into a slug."""
    return re.sub(r"[\W_]+", "_", text).strip("_")


@dataclasses.dataclass
class Folder:
    """A helper type for a folder."""

    id: str
    parent_id: str
    title: str
    icon: str

    def get_url(self) -> str:
        """Return the folder's relative URL."""
        return slugify(self.title)

    def get_summary_line(self, level: int) -> str:
        """Get the appropriate summary file line for this folder."""
        return ("    " * (level - 1)) + f"- {self.icon} {self.title}"

    def __lt__(self, other: Union["Folder", "Note"]) -> bool:
        """Support comparison, for sorting."""
        if isinstance(other, Note):
            # Folders always come before notes.
            return True
        if other.title == args.blog:
            return False
        return self.title.lower() < other.title.lower()

    def __repr__(self) -> str:
        """Pretty-print this class."""
        return f"Folder: <{self.title}>"


@dataclasses.dataclass
class Note:
    """A helper type for a note."""

    id: str
    folder: Folder
    title: str
    body: str
    updated_time: datetime
    created_time: datetime
    tags: List[str] = dataclasses.field(default_factory=list)

    def is_public(self) -> bool:
        """
        Check whether a note has tag public.

        This function checks a note's tags and returns whether it
        should be published.
        """
        keywords = ["public"]
        for keyword in keywords:
            if keyword in self.tags:
                return True
        return False
    
    def is_hidden(self) -> bool:
        """
        Check whether a note has tag hidden.

        This function checks a note's tags and returns whether it
        should be hidden.
        """
        keywords = ["hidden"]
        for keyword in keywords:
            if keyword in self.tags:
                return True
        return False

    def is_blog(self) -> bool:
        if self.folder.title == args.blog:
            return True
        return False

    def get_url(self) -> str:
        """Return the note's relative URL."""
        return slugify(self.folder.title) + "/" + slugify(self.title)

    def get_summary_line(self, level: int) -> str:
        """
        Get the appropriate summary file line for this note.

        The introduction is level 0, and is treated differently here.
        """
        return (
                "    " * (level - 1)
        ) + f"{'- ' if level > 0 else ''}[{self.title}]({self.get_url()}.md)"

    def __lt__(self, other: Union["Folder", "Note"]) -> bool:
        """Support comparison, for sorting."""
        if other.is_blog():
            return self.created_time > other.created_time
        else:
            return self.title.lower() < other.title.lower()

    def __repr__(self) -> str:
        """Pretty-print this class."""
        return f"Note: <{self.title}>"


@dataclasses.dataclass
class Resource:
    """A helper type for a resource."""

    title: str
    # The actual extension that the file stored in Joplin has.
    extension: str
    mimetype: str

    @property
    def derived_ext(self):
        """Return an extension derived from the resource's mime type."""
        ext = mimetypes.guess_extension(self.mimetype, strict=False)
        return "" if ext is None else ext


class JoplinExporter:
    """The main exporter class."""
    index_dir = Path(args.docsify)
    index_dir.mkdir(parents=True, exist_ok=True)
    content_dir = Path(f"{args.docsify}/joplin-notes")
    static_dir = Path(f"{args.docsify}/joplin-resources")
    joplin_dir = Path(args.joplin)

    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.used_resources: Set[str] = set()

        # A mapping of {"note_id": Note()}.
        self.note_lookup_dict: Dict[str, Note] = {}

        # A mapping of {"folder_id": Folder()}.
        self.folders: Dict[str, Folder] = {}

        # A mapping of {"folder_id": [Note(), Note()]}.
        self.notes: Dict[str, List[Note]] = defaultdict(list)

    def clean_content_dir(self):
        """Reset the content directory to a known state to begin."""
        rmtree(self.content_dir, ignore_errors=True)
        rmtree(self.static_dir, ignore_errors=True)
        self.content_dir.mkdir(parents=True)
        self.static_dir.mkdir(parents=True)

    def resolve_note_links(self, note: Note) -> str:
        """Resolve the links between notes and replace them in the body."""

        def replacement(match):
            item_id = match.group(1)
            new_url = self.get_note_url_by_id(item_id)
            
            if new_url:
                # new_url += ".html"
                return f"](<{new_url}>)"
            else:
                if note.folder.id:
                    note_dir = self.parents_path(note.folder.id)
                else:
                    note_dir = ""
                new_url = self.copy_resources_and_return_url(item_id, note_dir)
                if not new_url:
                    new_url = item_id
            
            if match.group(2):
                new_url += match.group(2)
           
            if Path(new_url).suffix in {".html", ".htm", ".markdown", ".md", ".mp3", ".mp4", ".ogg"}:
                embed = " ':include'"
            else:
                embed = " ':ignore :target=_blank'"

            return f"]({new_url}{embed})"

        return re.sub(r"\]\(:/([a-f0-9]{32})(#.*?)?\)", replacement, note.body)

    def copy_resources_and_return_url(self, resource_id: str, note_dir) -> Optional[str]:
        resource = self.resources.get(resource_id)
        if not resource:
            return None

        src = Path(f"{self.joplin_dir}/resources/{resource_id}.{resource.extension}")
        dst = Path(f"{self.content_dir}/{note_dir}/resources/{resource_id}{resource.derived_ext}")

        Path(f"{self.content_dir}/{note_dir}/resources").mkdir(parents=True, exist_ok=True)
        copy(src,dst)

        # Add the resource to the set of used resources, so we can only copy
        # the resources that are used.
        self.used_resources.add(resource_id)
        return Path(f"resources/{resource_id}{resource.derived_ext}")

    def get_note_url_by_id(self, note_id: str) -> Optional[str]:
        """Return a note's relative URL by its ID."""
        note = self.note_lookup_dict.get(note_id)
        if not note:
            return None
        return f"{self.parents_path(note.folder.id)}/{note.title}"

    def get_resource_url_by_id(self, resource_id: str) -> Optional[str]:
        """Return a resource's relative URL by its ID."""
        resource = self.resources.get(resource_id)
        if not resource:
            return None
        # Add the resource to the set of used resources, so we can only copy
        # the resources that are used.
        self.used_resources.add(resource_id)
        return "joplin-resources/" + resource_id + resource.derived_ext

    def copy_resources(self):
        """Copy all the used resources to the output directory."""
        for resource_id in self.used_resources:
            resource = self.resources[resource_id]
            copy(
                self.joplin_dir / "resources" /
                (f"{resource_id}.{resource.extension}"),
                self.static_dir / f"{resource_id}{resource.derived_ext}",
            )

    def check_new(self, seq):
        seq_file = self.index_dir / "sequence.txt"
        seq_file.touch()
        with (seq_file).open(mode="r+", encoding="utf-8") as outfile:
            if outfile.read() == seq and not args.force:
                quit()
            else:
                outfile.seek(0, 0)
                outfile.truncate()
                outfile.write(str(seq))

    def read_data(self):
        """Read the data from the Joplin database."""
        conn = sqlite3.connect(self.joplin_dir / "database.sqlite")
        c = conn.cursor()

        c.execute("""SELECT seq FROM sqlite_sequence WHERE name='item_changes';""")
        self.check_new(str(c.fetchone()[0]))

        c.execute("""SELECT id, title, parent_id, icon FROM folders;""")
        self.folders = {
            id: Folder(
                id, parent_id, title, json.loads(icon).get("emoji", "") if icon else ""
            )
            for id, title, parent_id, icon in c.fetchall()
        }

        self.folders = {
            id: folder for id, folder in self.folders.items()
        }

        # Get the tags by ID.
        c.execute("""SELECT id, title FROM tags;""")
        tags = {id: title for id, title in c.fetchall()}
        # Get the tag IDs for each note ID.
        c.execute("""SELECT note_id, tag_id FROM note_tags;""")
        note_tags = defaultdict(list)
        for note_id, tag_id in c.fetchall():
            note_tags[note_id].append(tags[tag_id])

        c.execute("""SELECT id, title, mime, file_extension FROM resources;""")

        self.resources = {
            id: Resource(
                title=title,
                extension=ext,
                mimetype=mime,
            )
            for id, title, mime, ext in c.fetchall()
        }

        c.execute(
            """SELECT id, parent_id, title, body, updated_time, created_time FROM notes;""")
        for id, parent_id, title, body, updated_time, created_time in c.fetchall():
            if parent_id not in self.folders:
                # This note is in a private folder, continue.
                continue

            note = Note(
                id,
                self.folders[parent_id],
                title,
                body,
                datetime.fromtimestamp(updated_time / 1000),
                datetime.fromtimestamp(created_time / 1000),
                tags=note_tags[id],
            )

            self.notes[note.folder.id].append(note)
            self.note_lookup_dict[note.id] = note

        conn.close()

    def write_summary(self):
        """Write the _sidebar.md for Docsify."""
        # We construct a note tree by adding each note into its parent.
        #note_tree: Dict[str, List[Union[Note, Folder]]] = defaultdict(list)

        # The note tree is a list of notes with their parents:
        # [
        #     [parent1, parent2, note1]
        #     [parent1, parent3, note2]
        # ]
        # Then, we sort these by alphabetical order, and we're done.
        note_tree = []
        introduction: Optional[Note] = None  # The "introduction" note.
        folders: List[Folder] = list
        for note_list in self.notes.values():
            for note in note_list:
                if "public homepage" in note.tags:
                    introduction = note
                    continue
                if not note.is_public():
                    continue
                note_item = [note]
                item: Union[Folder, Note] = note
                while True:
                    if isinstance(item, Note):
                        if item.is_hidden():
                            break
                        else:
                            item = item.folder
                    elif isinstance(item, Folder):
                        item = self.folders.get(item.parent_id)
                        if not item:
                            break
                    note_item.insert(0, item)

                note_tree.append(note_item)
        note_tree.sort()


        # Generate the sidebar file.
        items = []
        news = []
        latest = []
        ids = []
        for note_list in note_tree:
            lvl = 0
            for branch in note_list:
                lvl += 1
                if isinstance(branch, Folder):
                    if branch.id not in ids:
                        items.append(branch.get_summary_line(lvl))
                        ids.append(branch.id)
                elif isinstance(branch, Note) and not branch.is_hidden():
                    news.append(branch)
                    items.append(("    " * (lvl - 1)) + f"{'- ' if lvl > 0 else ''}[{branch.title}](<{self.parents_path(branch.folder.id)}/{branch.title}>)")


        with (self.content_dir / "_sidebar.md").open(mode="w", encoding="utf-8") as outfile:
            outfile.write(f"- [{args.name}](/)\n")
            outfile.write("\n".join(items))

        for new in sorted(news, key=lambda n: n.created_time, reverse=True):
            latest.append(
                f"[{new.title}](<{self.parents_path(new.folder.id)}/{new.title}>) ({new.created_time:%c})")


        with (self.content_dir / "README.md").open(mode="w", encoding="utf-8") as outfile:
            if introduction:
                introduction.folder.id = ""
                outfile.write(
                    f"""{self.resolve_note_links(introduction)}\n\n""")
                if not args.disable_latest:
                    outfile.write("Latest pages:\\\n")
                    outfile.write(f"\\\n".join(latest))
            else:
                if not args.disable_latest:
                    outfile.write("Latest pages:\\\n")
                    outfile.write(f"\\\n".join(latest))
                else:
                    # Docsify needed non-empty README.md to work. So let's add invisible non-breaking space.
                    outfile.write('&nbsp;')

    def export(self):
        """Export all the notes to a static site."""
        self.read_data()
        folder_list = sorted(self.folders.values())
        self.clean_content_dir()
        for folder in folder_list:
            for note in sorted(self.notes[folder.id], key=lambda n: n.title):
                if note.is_public():
                    note_dir = self.content_dir / self.parents_path(note.folder.id)
                    print(f"Exporting note: {self.parents_path(note.folder.id)}/{note.title}")
                    note_dir.mkdir(parents=True, exist_ok=True)
                    with (note_dir / (note.title + ".md")).open(mode="w", encoding="utf-8") as outfile:
                        outfile.write(
                            f"""{"# Hidden Page\n" if note.is_hidden() else ""}> Created: {note.created_time:%c}, updated: {note.updated_time:%c}, in {self.parents_path(note.folder.id)}\n# {note.title}\n{self.resolve_note_links(note)}""")
        self.write_summary()
#        self.copy_resources()
        if not args.save_index:
            self.write_html()

    def parents(self, id: str):
        """Return list of parent folders titles"""
        parents = []
        parents.append(self.folders[id].title)
        def parent(id):
            if self.folders[id].parent_id:
                parents.append(self.folders[self.folders[id].parent_id].title)
                parent(self.folders[self.folders[id].parent_id].id)
            return parents

        return parent(id)

    def parents_path(self, id: str):
        return "/".join(reversed(self.parents(id)))

    def write_html(self):
        if args.disable_cdn:
            docsify_path = ""
        else:
            docsify_path = "//cdn.jsdelivr.net/npm/docsify@4/"
            
        with (self.index_dir / "index.html").open(mode="w", encoding="utf-8") as outfile:
            outfile.write(f"""
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta charset="UTF-8" />
  <link 
    rel="stylesheet" 
    href="{docsify_path}lib/themes/{args.theme}.css" 
  />
</head>
<body>
  <div id="app"></div>
  <script>
    window.$docsify = {{
      basePath: "joplin-notes",
      alias: {{
        '/.*/_sidebar.md': '/_sidebar.md'
      }},
      loadSidebar: true,
      subMaxLevel: 10,
      search: 'auto',
/*      markdown: {{
        renderer: {{
          image: function (href, title, text) {{
            return `<img src="${{href}}" data-origin="${{href}}" alt="${{text}}">`
          }}
        }}
      }},*/
    }}
  </script>
  <script src="{docsify_path}lib/docsify.min.js"></script>
  <script src="{docsify_path}lib/plugins/search.min.js"></script>
  <script src="{docsify_path}lib/plugins/zoom-image.min.js"></script>
</body>
</html>
            """)


if __name__ == "__main__":
    print("Exporting Joplin database...")
    JoplinExporter().export()
