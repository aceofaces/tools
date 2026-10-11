---
title: River Flow
description: Animate how fast the Mississippi moves at seven stops from Minneapolis to the Gulf, using a flow model fed by OpenStreetMap water outlines and live USGS gauges.
tags: [maps, rivers, simulation]
---

Inspired by "The Niagara River, in Motion" videos: satellite imagery with the
water colored by speed and white streaks drifting downstream. Step through the
stops with the arrows, or pan and zoom: the model follows the map, re-solving
for whatever is in view once it settles. Tap the water to see the modeled speed
and estimated depth. `#stop=new-orleans` links to a stop.

How each view is modeled:

- **Where the water is.** Water polygons come from OpenStreetMap through
  [OpenFreeMap](https://openfreemap.org) vector tiles. They're rasterized onto
  a grid of 460 cells along the long side of the visible map plus a margin.
  Views wider than about 90 km aren't modeled; the rivers get too thin.
- **Where it comes in and goes out.** OpenStreetMap river centerlines are drawn
  downstream, so where a named one crosses into the view is an inlet and where
  one crosses out is an outlet. Other edges are walls, unless no centerline
  leaves the view (the open Gulf), in which case all of them are outlets.
- **How much water.** Each inlet takes the latest reading from the nearest USGS
  gauge on the river of the same name. If a gauge can't be reached, a typical flow is used and
  the page says so.
- **How it moves.** This is a steady, depth-averaged model in which bed friction
  balances the water-surface slope (Manning's equation, so conveyance scales
  with depth^5/3) and water is conserved. Gauge discharge enters where the river
  crosses into the map and leaves where it crosses out. Banks and islands are
  walls. The solver is conjugate gradients.
- **Depth is a guess.** There's no bathymetry. Depth rises with distance from
  shore up to a per-stop channel depth. Speeds are plausible, not measured.

The model has no momentum, so it misses eddies, flow separation behind wing
dikes and how currents hug the outside of bends. Locks, dams and spillways
are treated as open water. The animation is a time-lapse; the details line
under the map gives the factor.

Adding another river means adding an entry to `RIVERS` in the page, with a
bounding box per stop and its gauges: the river's name as OpenStreetMap spells
it (minus "River"), a USGS site number and roughly where that water enters.
