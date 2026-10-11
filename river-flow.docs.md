---
title: River Flow
description: Animate how fast the Mississippi moves at seven stops from Minneapolis to the Gulf, using a flow model fed by OpenStreetMap water outlines and live USGS gauges.
tags: [maps, rivers, simulation]
---

Inspired by "The Niagara River, in Motion" videos: satellite imagery with the
water colored by speed and white streaks drifting downstream. Step through the
stops with the arrows. Tap the water to see the modeled speed and estimated depth.
`#stop=new-orleans` links to a stop.

How each stop is modeled:

- **Where the water is.** Water polygons come from OpenStreetMap through
  [OpenFreeMap](https://openfreemap.org) vector tiles. They're rasterized onto
  a grid of about 380 cells along the long side of the stop.
- **How much water.** Discharge is the latest reading from the USGS gauge for
  each inflowing river. If a gauge can't be reached, a typical flow is used and
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
bounding box per stop, inlet points with USGS site numbers, and outlet points.
