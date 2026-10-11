import json
import re

import pytest
from playwright.sync_api import expect

TILEJSON = {"tiles": ["https://tiles.openfreemap.org/test/{z}/{x}/{y}.pbf"], "maxzoom": 14}


# A minimal Mapbox Vector Tile encoder, enough to build a "water" layer fixture.
def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def field(num, wire, payload):
    if wire == 0:
        return varint(num << 3) + varint(payload)
    return varint(num << 3 | 2) + varint(len(payload)) + payload


def zigzag(n):
    return (n << 1) ^ (n >> 31)


def ring(points):
    geom, x, y = [], 0, 0
    for k, (px, py) in enumerate(points):
        if k == 0:
            geom.append(1 | 1 << 3)
        elif k == 1:
            geom.append(2 | (len(points) - 1) << 3)
        geom += [zigzag(px - x), zigzag(py - y)]
        x, y = px, py
    geom.append(7 | 1 << 3)
    return geom


def feature(value_index, rings):
    geom = [g for r in rings for g in ring(r)]
    return (
        field(2, 2, b"".join(varint(t) for t in [0, value_index]))
        + field(3, 0, 3)
        + field(4, 2, b"".join(varint(g) for g in geom))
    )


def line(points):
    geom, x, y = [1 | 1 << 3], 0, 0
    for k, (px, py) in enumerate(points):
        if k == 1:
            geom.append(2 | (len(points) - 1) << 3)
        geom += [zigzag(px - x), zigzag(py - y)]
        x, y = px, py
    return geom


def line_feature(tags, points):
    return (
        field(2, 2, b"".join(varint(t) for t in tags))
        + field(3, 0, 2)
        + field(4, 2, b"".join(varint(g) for g in line(points)))
    )


def water_tile():
    # A river band across the tile with a square island in it (a hole, counterclockwise),
    # crossed by a band running down the tile, so tiles join up into a lattice of channels
    river = feature(0, [
        [(-64, 1400), (4160, 1400), (4160, 2700), (-64, 2700)],
        [(3000, 1800), (3000, 2300), (3500, 2300), (3500, 1800)],
    ])
    cross = feature(0, [[(1400, -64), (2700, -64), (2700, 4160), (1400, 4160)]])
    # A swimming pool covering the whole tile must be ignored
    pool = feature(1, [[(0, 0), (4096, 0), (4096, 4096), (0, 4096)]])
    layer = (
        field(15, 0, 2)
        + field(1, 2, b"water")
        + field(2, 2, river)
        + field(2, 2, cross)
        + field(2, 2, pool)
        + field(3, 2, b"class")
        + field(4, 2, field(1, 2, b"river"))
        + field(4, 2, field(1, 2, b"swimming_pool"))
        + field(5, 0, 4096)
    )
    # Centerlines, drawn downstream: the "Mississippi River" flows east along the band,
    # an ungauged river flows south down the cross band
    waterway = (
        field(15, 0, 2)
        + field(1, 2, b"waterway")
        + field(2, 2, line_feature([0, 0, 1, 1], [(-64, 2050), (4160, 2050)]))
        + field(2, 2, line_feature([0, 0, 1, 2], [(2050, -64), (2050, 4160)]))
        + field(3, 2, b"class")
        + field(3, 2, b"name")
        + field(4, 2, field(1, 2, b"river"))
        + field(4, 2, field(1, 2, b"Mississippi River"))
        + field(4, 2, field(1, 2, b"Nameless Bayou"))
        + field(5, 0, 4096)
    )
    return field(3, 2, layer) + field(3, 2, waterway)


def usgs_ok(route):
    site = re.search(r"USGS-(\d+)", route.request.url).group(1)
    body = {"features": [{"properties": {"value": "400000", "time": "2026-10-11T12:00:00Z", "site": site}}]}
    route.fulfill(body=json.dumps(body), content_type="application/json")


@pytest.fixture
def river(page):
    page.route("https://server.arcgisonline.com/**", lambda r: r.abort())
    page.route("https://tiles.openfreemap.org/planet",
               lambda r: r.fulfill(body=json.dumps(TILEJSON), content_type="application/json"))
    tile = water_tile()
    page.route("https://tiles.openfreemap.org/test/**",
               lambda r: r.fulfill(body=tile, content_type="application/x-protobuf"))
    page.route("https://api.waterdata.usgs.gov/**", usgs_ok)
    page.route("https://waterservices.usgs.gov/**", lambda r: r.fulfill(status=500))
    return page


def model(page):
    return page.evaluate("""() => {
        const m = riverFlow.state.model;
        let active = 0; for (const a of m.active) active += a;
        return { inflow: m.inflow, outflow: m.outflow, max: m.max, p95: m.p95,
                 active, cells: m.grid.W * m.grid.H, rel: m.rel, bbox: m.grid.bbox,
                 inlets: m.inlets.map(g => g.gauge.site) };
    }""")


def test_models_flow_from_vector_tiles(river, server):
    river.goto(f"{server}/river-flow.html#stop=new-orleans")
    expect(river.locator("#cap-title")).to_have_text("Algiers Point")
    expect(river.locator("#cap-sub")).to_contain_text("400,000 cubic feet a second")
    expect(river.locator("#busy")).to_be_hidden()
    expect(river.locator("#error")).to_be_empty()
    m = model(river)
    # Mass balance: what leaves the outlet is what the gauge put in
    assert m["outflow"] == pytest.approx(m["inflow"], rel=0.01)
    # The pool covering every tile isn't water
    assert 0 < m["active"] < m["cells"] * 0.7
    # 400,000 cfs through ~750 m wide, up to 30 m deep channels: a few mph
    assert 0.3 < m["p95"] * 2.237 < 8
    expect(river.locator("#details")).to_contain_text("400,000 ft³/s")


def test_two_inlets_share_the_flow(river, server):
    river.goto(f"{server}/river-flow.html#stop=cairo")
    expect(river.locator("#busy")).to_be_hidden()
    expect(river.locator("#error")).to_be_empty()
    expect(river.locator("#cap-sub")).to_have_text("The Ohio brings 50% of the water at Cairo")
    m = model(river)
    assert m["outflow"] == pytest.approx(m["inflow"], rel=0.01)


def test_falls_back_to_typical_flow(river, server):
    river.route("https://api.waterdata.usgs.gov/**", lambda r: r.fulfill(status=503))
    river.goto(f"{server}/river-flow.html#stop=st-louis")
    expect(river.locator("#details")).to_contain_text("gauge unavailable, using a typical 190,000")
    expect(river.locator("#cap-sub")).to_contain_text("190,000 cubic feet every second")


def test_tile_failure_is_shown(river, server):
    river.route("https://tiles.openfreemap.org/test/**", lambda r: r.fulfill(status=500))
    river.goto(f"{server}/river-flow.html")
    expect(river.locator("#error")).to_contain_text("Couldn't model St. Anthony Falls")
    expect(river.locator("#busy")).to_be_hidden()


def test_navigation_updates_hash(river, server):
    river.goto(f"{server}/river-flow.html")
    expect(river.locator("#prev")).to_be_disabled()
    river.click("#next")
    expect(river.locator("#cap-title")).to_have_text("The Missouri Joins")
    assert river.url.endswith("#river=mississippi&stop=missouri")
    expect(river.locator(".stops button[aria-current=true]")).to_have_text("Missouri confluence")


def test_model_follows_the_map(river, server):
    river.goto(f"{server}/river-flow.html#stop=memphis")
    expect(river.locator("#busy")).to_be_hidden()
    first = model(river)
    assert first["inlets"] and set(first["inlets"]) == {"07032000"}
    # Pan well past the modeled area: a new model covers the new view
    river.evaluate("riverFlow.map.panBy([2000, 1500], { animate: false })")
    river.wait_for_function("""() => {
        const m = riverFlow.state.model, b = riverFlow.map.getBounds(), [s, w, n, e] = m.grid.bbox;
        return b.getSouth() >= s && b.getWest() >= w && b.getNorth() <= n && b.getEast() <= e;
    }""")
    expect(river.locator("#busy")).to_be_hidden()
    expect(river.locator("#error")).to_be_empty()
    m = model(river)
    assert m["bbox"] != first["bbox"]
    assert m["outflow"] == pytest.approx(m["inflow"], rel=0.01)


def test_zoomed_out_too_far_keeps_the_model(river, server):
    river.goto(f"{server}/river-flow.html#stop=st-louis")
    expect(river.locator("#busy")).to_be_hidden()
    first = model(river)
    river.evaluate("riverFlow.map.setZoom(7, { animate: false })")
    expect(river.locator("#busy")).to_have_text("Zoom in to model the flow here")
    assert model(river)["bbox"] == first["bbox"]
    expect(river.locator("#error")).to_be_empty()
