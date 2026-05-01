# Standard Library
from pathlib import Path


def create_sample_html(dest: Path) -> None:
    """Create a minimal structured HTML file at *dest*.

    Structure mirrors sample.md and sample.docx:
      H1 "Sample Document", H2 "Introduction" / "Data Overview" / "Conclusion",
      one image and one table under Data Overview.

    Image src is a relative path string (base64 encoding is a future enhancement).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Sample Document</title></head>
<body>

<h1>Sample Document</h1>

<h2>Introduction</h2>
<p>This is the introduction paragraph.</p>

<h2>Data Overview</h2>
<p>This section covers data.</p>

<img src="sample_image.png" alt="Sample Image">

<table>
  <tr><th>Name</th><th>Value</th></tr>
  <tr><td>Alpha</td><td>1</td></tr>
  <tr><td>Beta</td><td>2</td></tr>
</table>

<h2>Conclusion</h2>
<p>Final remarks go here.</p>

</body>
</html>
""", encoding="utf-8")
