# Saving things

An entry is one thing you want to keep: a page you mean to read, a watch
you are pricing, a recipe. It holds a web address, a title, some notes,
and any tags you give it.

## Saving something

Sign in and you land on your entries. "Save something" asks for:

- **Address** — where it is on the web. The only thing actually
  required.
- **Title** — what to call it. Leave it blank and Hrček shows the
  address instead.
- **Notes** — anything you want to remember. Plain text; line breaks are
  kept.
- **Tags** — separated by commas.

## Saving the same address twice

**If you save an address you already have, Hrček updates that entry
instead of making a second one.** This is deliberate: it means a script
or an import can be re-run without doubling everything.

It is also worth knowing before it surprises you. Re-saving a page with
an empty notes box replaces the notes you had written. If you want to
add to an entry, edit it rather than saving the address again.

Two different people saving the same address is unrelated. Your entries
are yours.

## Tags

Tags are your own: nobody else sees them, and nobody else's appear in
your list. Capitals do not make a tag different — `Watches` and
`watches` are the same tag, and the first spelling you used is the one
shown.

Click a tag to see only the entries carrying it.

**A tag stops existing once nothing uses it.** Take the last entry off
`diving` and the tag disappears. This keeps the list from filling up
with typos; it also means a tag is not a place to keep something.

## Editing and deleting

Every entry has an "Edit" link. Deleting asks first, and **cannot be
undone** — there is no trash to recover from.

## Entries and scripts

If you use Hrček from a script, see [the API guide](../dev/api.md). A
script can save one entry or a batch of them, and saving works the same
way: an address you already hold is updated.
