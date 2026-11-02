#!/usr/bin/env python3
"""Render README SVGs locally from saved measurements and vector scenes.

No model, network, browser, or third-party Python package is used. Historical
scenes retain measured labels, geometry and real viewer screenshots; the shared
frame and typography are generated here. Pilot bars are computed from usage data.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'bench' / 'diagram_sources'
THEME = json.loads((SOURCES / 'theme.json').read_text())
WIDTH = 1040
FONT = "Inter,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif"


def element(tag, parent=None, text=None, **attrs):
    node = ET.Element(tag, {k.replace('_', '-'): str(v) for k, v in attrs.items()})
    node.text = str(text) if text is not None else None
    if parent is not None:
        parent.append(node)
    return node


class Canvas:
    """Shared hey.trading frame, typography and chart primitives."""

    def __init__(self, height, title, label, description, subtitle=''):
        self.root = element('svg', xmlns='http://www.w3.org/2000/svg',
                            width=WIDTH, height=height, viewBox=f'0 0 {WIDTH} {height}',
                            role='img', aria_labelledby='title desc')
        element('title', self.root, title, id='title')
        element('desc', self.root, description, id='desc')
        element('style', self.root,
                f'text{{font-family:{FONT};font-variant-numeric:tabular-nums}}'
                '.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}')
        defs = element('defs', self.root)
        wash = element('linearGradient', defs, id='theme-wash', x2='1', y2='1')
        for offset, color in [('0', 'warm_wash'), ('.6', 'background'), ('1', 'soft_green')]:
            element('stop', wash, offset=offset, stop_color=THEME[color])
        self.rect(0, 0, WIDTH, height, 'url(#theme-wash)', 28)
        self.group = element('g', self.root, fill=THEME['ink'])
        title_lines = textwrap.wrap(title, 61)
        sub_lines = textwrap.wrap(subtitle, 112)
        self.header_bottom = 115 + 36 * (len(title_lines) - 1) + 22 * len(sub_lines)
        self.card(24, 24, 992, self.header_bottom - 24)
        self.text(52, 58, 'COMPOUND  /  ' + label, 13, 'green', 650)
        for i, line in enumerate(title_lines):
            self.text(52, 98 + i * 36, line, 28, weight=750)
        for i, line in enumerate(sub_lines):
            self.text(52, 128 + (len(title_lines) - 1) * 36 + i * 22, line, 14, 'muted')

    def rect(self, x, y, width, height, fill, radius=0, parent=None, **attrs):
        return element('rect', parent if parent is not None else getattr(self, 'group', self.root),
                       x=x, y=y, width=width, height=height, rx=radius,
                       fill=THEME.get(fill, fill), **attrs)

    def card(self, x, y, width, height):
        return self.rect(x, y, width, height, 'card', 28,
                         stroke=THEME['line'], stroke_width=1)

    def text(self, x, y, value, size=18, color='ink', weight=400, parent=None):
        return element('text', parent if parent is not None else self.group,
                       value, x=x, y=y, font_size=size, font_weight=weight,
                       fill=THEME.get(color, color))

    def pair(self, y, values, displays, maximum, label='Go allowance · lower is better'):
        self.text(52, y, label, 19, weight=650)
        for i, (value, display) in enumerate(zip(values, displays)):
            row_y = y + 38 + i * 62
            self.text(52, row_y + 22, ['Without Compound', 'With Compound'][i], 17, weight=600)
            self.rect(286, row_y, 510, 32, 'background_secondary', 16)
            self.rect(286, row_y, 510 * float(value / maximum), 32,
                      'baseline' if i == 0 else 'green', 16)
            self.text(820, row_y + 24, display, 23,
                      'ink' if i == 0 else 'green', 700)

    def svg(self):
        ET.indent(self.root, space='  ')
        return ET.tostring(self.root, encoding='unicode') + '\n'


def inflate(source):
    attrs = dict(source['attrs'])
    href = attrs.get('href', '')
    if href.startswith('screenshot:'):
        image = SOURCES / 'screenshots' / href.removeprefix('screenshot:')
        media_type = 'image/webp' if image.name.endswith('.webp.b64') else 'image/png'
        attrs['href'] = 'data:' + media_type + ';base64,' + ''.join(image.read_text().split())
    # Source paint attributes remain authoritative; CSS must not override them.
    node = ET.Element(source['tag'], attrs)
    node.text = source.get('text')
    for child in source.get('children', []):
        node.append(inflate(child))
    return node


def historical(path):
    source = json.loads(path.read_text())
    nodes = [inflate(n) for n in source['nodes']]
    subtitle = ''
    crop = 0
    if path.stem in {'benchmark-heldout', 'benchmark-real16', 'benchmark-map',
                     'benchmark-rule', 'benchmark-answers', 'benchmark-compared'}:
        crop = 96 if path.stem == 'benchmark-rule' else 113
        headers = [n for n in nodes if n.tag == 'text' and float(n.get('y', '999')) < crop]
        subtitle = ' '.join(n.text or '' for n in headers[1:])
        nodes = [n for n in nodes if n not in headers]
    if path.stem == 'map-context':
        crop = 144
        for node in nodes:
            if node.tag == 'g':
                for child in list(node):
                    if (child.tag == 'rect' and child.get('y') == '24') or (child.tag == 'text' and child.get('y') in {'68', '104'}):
                        node.remove(child)
        subtitle = '15 offline query pairs · 5 pinned repos · identical map metadata'
    if path.stem == 'code-map':
        crop = 60
        nodes = [n for n in nodes if n.tag != 'text']
        source['title'] = 'Explore the code. Keep the context.'
    _, _, width, height = map(float, source['viewBox'].split())
    scale = 944 / width
    # Size the outer canvas from the shared header, then preserve the full scene.
    probe = Canvas(1, source['title'], source['label'], source['description'], subtitle)
    body_y = probe.header_bottom + 20
    total_height = round(body_y + (height - crop) * scale + 72)
    canvas = Canvas(total_height, source['title'], source['label'], source['description'], subtitle)
    canvas.card(24, body_y, 992, (height - crop) * scale + 40)
    group = element('g', canvas.group,
                    transform=f'translate(48 {body_y + 20 - crop * scale:.3f}) scale({scale:.6f})')
    # Prefix scene IDs to isolate paint servers from the common frame.
    for node in nodes:
        for child in node.iter():
            for key, value in list(child.attrib.items()):
                child.set(key, ('scene-' + value) if key == 'id' else value.replace('url(#', 'url(#scene-'))
        group.append(node)
    return canvas.svg()


def money(value):
    return Decimal(str(value))


def load_pilot():
    data = json.loads((SOURCES / 'pilot.json').read_text())
    for arm, total in data['arms'].items():
        for field in ['allowance_usd', 'list_cost_usd', 'requests']:
            observed = sum(money(task[arm][field]) for task in data['tasks'])
            if observed != money(total[field]):
                raise ValueError(f'Pilot {arm} {field}: task values do not sum to total')
        if sum(task[arm]['accepted'] for task in data['tasks']) != total['accepted']:
            raise ValueError(f'Pilot {arm}: accepted count differs')
    for total_key, field in [('total_experiment_allowance_usd', 'allowance_usd'),
                             ('total_experiment_list_cost_usd', 'list_cost_usd'),
                             ('total_experiment_requests', 'requests')]:
        observed = sum(money(arm[field]) for arm in data['arms'].values()) + money(data['invalid_setup_attempt'][field])
        if observed != money(data[total_key]):
            raise ValueError(f'Pilot {total_key}: experiment spend differs')
    return data


def pilots():
    data = load_pilot()
    arms = [data['arms'][arm] for arm in ['without', 'with']]
    values = [money(arm['allowance_usd']) for arm in arms]
    reduction = (1 - values[1] / values[0]) * 100
    meta = f"{data['compound_version']} · DeepSeek V4.1 Flash · Y Harness · 2 November 2026"
    accepted = [f"{a['accepted']}/{a['runs']}" for a in arms]
    requests = [str(a['requests']) for a in arms]
    mutations = [f"{a['mutants_caught']}/{a['mutants_total']}" for a in arms]
    scope = 'Two previously used Python tasks. One run per task and mode; order counterbalanced.'
    desc = (f'Two-task pilot: without Compound ${values[0]}, with Compound ${values[1]} of Go allowance; '
            f'{reduction:.1f}% less in the matched total. Both modes passed 2/2 tasks. '
            'Model requests: 21 without, 29 with. API cash charge $0 both on the Go subscription. '
            'One refund task cost more with Compound. No long-term savings measured.')
    chart = Canvas(710, f'Two tasks. {reduction:.1f}% less plan allowance.', 'MEASURED PILOT', desc, meta)
    chart.card(24, 158, 992, 272)
    chart.pair(197, values, [f'${v:.8f}' for v in values], max(values) * Decimal('1.08'))
    chart.text(52, 402, scope, 15, 'muted')
    chart.card(24, 450, 992, 150)
    for x, value, caption in [(52, f'{reduction:.1f}% less', 'matched Go allowance'),
                               (380, accepted[0] + ' each' if accepted[0] == accepted[1] else ' → '.join(accepted), 'tasks accepted'),
                               (708, ' → '.join(requests), 'model requests · without → with')]:
        chart.text(x, 501, value, 31, 'green' if x < 708 else 'ink', 750)
        chart.text(x, 540, caption, 15, 'muted')
    chart.text(52, 641, '$0 cash charge in both modes under the existing Go subscription.', 16, weight=600)
    chart.text(52, 672, 'Allowance measures plan capacity consumed. This pilot does not establish long-term savings.', 15, 'muted')
    yield 'benchmark-pilot-cost.svg', chart.svg()

    chart = Canvas(910, 'The task-level results', 'MEASURED PILOT', desc, meta)
    for i, task in enumerate(data['tasks']):
        y = 158 + i * 310
        chart.card(24, y, 992, 288)
        vals = [money(task[arm]['allowance_usd']) for arm in ['without', 'with']]
        change = (vals[1] / vals[0] - 1) * 100
        chart.text(52, y + 39, ['Refund bug fix', 'Retry-helper refactor'][i], 23, weight=700)
        chart.text(650, y + 39, f'{abs(change):.1f}% ' + ('more' if change > 0 else 'less') + ' allowance',
                   20, 'negative' if change > 0 else 'green', 700)
        chart.pair(y + 78, vals, [f'${v:.8f}' for v in vals], max(vals) * Decimal('1.08'))
        task_requests = ' / '.join(str(task[arm]['requests']) for arm in ['without', 'with'])
        chart.text(52, y + 258, f'Both passed · model requests without / with: {task_requests} · one pair', 16, 'muted')
    chart.text(52, 820, 'Same fixture revision, prompt, model, reasoning and limits within each pair.', 17, weight=600)
    chart.text(52, 853, 'Independent zero-based bar scales per task. Provider caches were not reset.', 15, 'muted')
    chart.text(52, 881, 'These are development fixtures, not newly held-out tasks. Four valid runs total.', 15, 'muted')
    yield 'benchmark-pilot-tasks.svg', chart.svg()

    chart = Canvas(756, 'Correctness and work performed', 'MEASURED PILOT', desc, meta)
    chart.card(24, 158, 992, 382)
    chart.text(52, 201, 'Graded outcomes', 23, weight=700)
    chart.text(610, 201, 'Without Compound', 17, 'muted', 600)
    chart.text(825, 201, 'With Compound', 17, 'green', 600)
    rows = [('Tasks accepted', *accepted),
            ('Hidden checks + original + final suites', 'All pass', 'All pass'),
            ('Original tests removed or weakened', '0', '0'),
            ('Planted wrong changes caught by tests', *mutations),
            ('Model requests', *requests), ('Tool calls', *(a['tool_calls'] for a in arms))]
    for i, (label, baseline, compound) in enumerate(rows):
        y = 247 + i * 45
        chart.text(52, y, label, 17)
        chart.text(650, y, baseline, 20, weight=650)
        chart.text(860, y, compound, 20, 'green', 650)
    chart.card(24, 560, 992, 114)
    chart.text(52, 600, 'Additional test-strength checks: ' + ' → '.join(mutations), 22, 'green', 700)
    chart.text(52, 635, 'Frozen mutation checks assess tests left behind; they are not extra successful tasks.', 15, 'muted')
    chart.text(52, 712, 'Compound used less allowance overall here while making more calls.', 17, weight=600)
    chart.text(52, 740, 'One run per task and mode cannot establish a general cost or quality improvement.', 15, 'muted')
    yield 'benchmark-pilot-correctness.svg', chart.svg()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if checked-in SVGs differ from their sources')
    parser.add_argument('--output', type=Path, default=ROOT / '.github' / 'assets')
    args = parser.parse_args()
    outputs = {p.stem + '.svg': historical(p) for p in sorted((SOURCES / 'scenes').glob('*.json'))}
    outputs.update(pilots())
    stale = []
    for name, svg in outputs.items():
        ET.fromstring(svg)
        path = args.output / name
        if args.check:
            if not path.exists() or path.read_text() != svg:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg)
    if stale:
        parser.exit(1, 'Regenerate README diagrams: ' + ', '.join(stale) + '\n')
    print(f'{"Verified" if args.check else "Rendered"} {len(outputs)} README SVGs; no model calls.')


if __name__ == '__main__':
    main()
