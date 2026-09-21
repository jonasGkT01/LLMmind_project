# 2026-09-21 — NSD dataset now includes many more images

## What changed

The NSD (Natural Scenes Dataset) brain-image data is processed differently
now, in a way that keeps far more of the available images usable.

Previously, an image could only be included in the analysis if **every one**
of the 8 NSD participants had seen it at least 3 times. That rule was
specific to NSD — no other dataset in this project works that way — and it
threw away most of the data: only 515 of the roughly 1,000 shared images
made it through.

Now NSD follows the same rule already used for the other datasets in this
project (like Caption Scene): an image is kept as long as there are at
least two brain-activity recordings of someone looking at it, no matter
which participant, and no matter how many times each participant saw it.
This is the minimum needed to check whether people's brains respond
similarly to an image at all — you can't compare a single recording to
itself. Below that minimum, an image simply can't be used; above it,
everything available is used.

We also fixed a related issue: when a participant saw the same image more
than once, those separate viewings were previously being stitched together
into one long, continuous brain recording, as if they happened back to
back. They didn't — they happened at different, often far-apart moments
during the experiment. Each viewing is now treated as its own separate,
independent recording, which is the more accurate way to combine them.

## What this means for you

- Many more NSD images are now available for analysis than before — not
  just the ~515 that previously met the strict 3-repetitions-for-everyone
  rule.
- Each image's number of usable recordings can now differ from image to
  image, and from participant to participant. That's expected: some images
  were shown more often, or to more participants, than others.
- The final output you consume is unchanged in shape: one brain-response
  summary per image, feeding into the same downstream comparisons
  (nearest-neighbour search, brain-model alignment) as before.

## Action needed

If you use NSD results, regenerate them by rerunning the pipeline — the
set of included images and how each image's brain response is computed
have both changed, so old NSD outputs are not compatible with this update
and should be treated as outdated.
