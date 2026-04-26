# Standard Library
from pathlib import Path

# Private Library
from tests.fixtures._image import minimal_png


def create_sample_pdf(dest: Path) -> None:
    """Create a minimal structured PDF at *dest* using pymupdf (fitz).

    Structure mirrors sample.docx and sample.md:
      H1 "Sample Document", H2 "Introduction" / "Data Overview" / "Conclusion",
      one GFM-style table and one embedded image under Data Overview.
    """
    import fitz

    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()

    TITLE_SIZE   = 24
    HEADING_SIZE = 16
    BODY_SIZE    = 11
    y = 50

    def write(text: str, size: float) -> None:
        nonlocal y
        page.insert_text((50, y), text, fontsize=size, fontname="helv", color=(0, 0, 0))
        y += size * 3.0  # large gap so each element lands in its own pymupdf text block

    write("Sample Document",                    TITLE_SIZE)
    write("Introduction",                        HEADING_SIZE)
    write("This is the introduction paragraph.", BODY_SIZE)
    write("Data Overview",                       HEADING_SIZE)
    write("This section covers data.",           BODY_SIZE)

    # Embed a small image
    page.insert_image(fitz.Rect(50, y, 90, y + 40), stream=minimal_png())
    y += 50

    # Draw a real grid table so page.find_tables() detects it
    col_widths = [80, 60]
    row_height = 18
    table_rows = [["Name", "Value"], ["Alpha", "1"], ["Beta", "2"]]
    col_x = [50, 50 + col_widths[0], 50 + sum(col_widths)]
    shape = page.new_shape()
    for ri in range(len(table_rows) + 1):
        ry = y + ri * row_height
        shape.draw_line((col_x[0], ry), (col_x[-1], ry))
    for cx in col_x:
        shape.draw_line((cx, y), (cx, y + len(table_rows) * row_height))
    shape.finish(color=(0, 0, 0), width=0.5)
    shape.commit()
    for ri, row in enumerate(table_rows):
        for ci, cell in enumerate(row):
            page.insert_text(
                (col_x[ci] + 3, y + ri * row_height + row_height - 4),
                cell, fontsize=BODY_SIZE, fontname="helv",
            )
    y += len(table_rows) * row_height + 40

    write("Conclusion",                          HEADING_SIZE)
    write("Final remarks go here.",              BODY_SIZE)

    doc.save(str(dest))
    doc.close()
