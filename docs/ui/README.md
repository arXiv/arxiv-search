#UI Reference Documents

Source files are accompanied by PDF or image files with the same naming
conventions to provide generic readability.

**Workflow documents** are a visualization of the screens and actions that a
user would take to perform a specific task (or complete a user story).

**Wireframe documents** are very simple layout structures to help define the
overall structure of a page and inform prototypes. They provide a high-level
overview, define regions, and prompt discussion of necessary details.

User interface
==========================

Search workflow for users follows a cyclic pattern, with an initial query
producing results which can be sorted, filtered, and inspected. For the initial
phase, focus is placed on query building, reformulation, and results display.

Search behaviors to promote: reformulation, orienteering, targeted search,
query refinement/drilldown.

Solutions that support these behaviors:
  - Query box with original query pre-filled on results page (reformulation)
  - Pagination (orienteering)
  - Sorting (refinement)
  - Advanced Search with specific field, category, and date options (targeting)
  - Author Search interim structure (orienteering)

Some design decisions are constrained by the choice to minimize JavaScript or
AJAX calls to the interface. Simplicity allows us to focus development and
testing on functionality first, then add interface enhancements in later
iterations. Examples: Go button required for results sorting, manual checkbox
toggle for related fields with input (dates, Physics subject dropdown), error
messages persistent until page reload even if corrections are made.
