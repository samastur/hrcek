# Collections

A collection is a named set of one person's entries. This page covers
the model; sharing and feeds arrive with those layers.

## Two kinds, one immutable choice

`Collection.kind` is either `manual` or `label`, and it is fixed at
creation. `CollectionForm` deletes the `kind` and `label` inputs once
the instance exists, so the edit page cannot offer them and a crafted
POST cannot set them either.

The database holds the shape as well, through a check constraint: a
label collection names exactly one label, a manual one names none.
The other two shapes are meaningless, so nothing may write them.

```python
models.CheckConstraint(
    condition=(
        Q(kind="label", label__isnull=False) | Q(kind="manual", label__isnull=True)
    ),
    name="label_set_exactly_when_kind_is_label",
)
```

## Membership

Manual membership is `CollectionEntry`, a model rather than a plain
many-to-many because it carries `added_at` — which is what orders a
manual collection. Label membership is not stored at all: it is a
query over the label, so an entry gaining or losing the label moves in
or out with nothing to keep in step.

`Collection.entries()` is the single source of both, and of their
orderings:

| Kind | Ordered by | Why |
|---|---|---|
| Manual | `CollectionEntry.added_at` | The moment it was put in |
| Label | `Entry.created_at` | There is no moment of adding |

Pages, feeds and tests all call this method. Nothing re-implements the
ordering, so nothing can drift out of step with it.

## Ownership

`services.add_entry` is the only way an entry joins a collection, and
it refuses across accounts with `HRC-COLL-0001` — a 404 code, not a
403, on the project's usual reasoning that a 403 confirms the thing
exists. It also refuses to add by hand to a label collection
(`HRC-COLL-0002`), which the pages never offer but a direct POST
could try.

Adding twice is deliberately harmless: the page lists each entry once,
and a double submission should not become an error somebody has to
read.

## Deleting

Deleting a collection cascades to its `CollectionEntry` rows and stops
there. The entries themselves are untouched, which the confirmation
page says in as many words.
