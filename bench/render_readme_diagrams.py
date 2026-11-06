#!/usr/bin/env python3
"""Render README SVGs locally from saved measurements and vector scenes.

No model, network, browser, or third-party Python package is used. Historical
scenes retain measured labels, geometry and real viewer screenshots; the shared
frame and typography are generated here. Pilot bars are computed from usage data.
"""
from __future__ import annotations

import argparse
import hashlib
from decimal import Decimal
import json
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET

from yharness_verdict import evaluate

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

    def pair(self, y, values, displays, maximum, label='Go allowance · lower is better',
             modes=('Without Compound', 'With Compound')):
        self.text(52, y, label, 19, weight=650)
        for i, (value, display) in enumerate(zip(values, displays)):
            row_y = y + 38 + i * 62
            self.text(52, row_y + 22, modes[i], 17, weight=600)
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


def load_workflow():
    data = json.loads((SOURCES / 'workflow.json').read_text())
    if len(data['sequences']) != 2 or any(len(sequence['stages']) != 3 for sequence in data['sequences']):
        raise ValueError('Workflow requires two three-change sequences')
    fields = ['requests', 'tool_calls', 'semantic_repairs', 'transport_resumes', 'unknown_usage_requests']
    for sequence in data['sequences']:
        for stage in sequence['stages']:
            for arm in ['without', 'with']:
                for field in fields:
                    if sum(attempt[field] for attempt in stage[arm]['attempts']) != stage[arm][field]:
                        raise ValueError('Workflow must retain all initial, failed and recovery attempts')
                if sum(money(attempt['known_allowance_usd']) for attempt in stage[arm]['attempts']) != money(stage[arm]['known_allowance_usd']):
                    raise ValueError('Workflow attempt costs differ from stage total')
        for arm in ['without', 'with']:
            total = sequence['arms'][arm]
            stages = [stage[arm] for stage in sequence['stages']]
            for field in fields:
                if sum(stage[field] for stage in stages) != total[field]:
                    raise ValueError(f'Workflow {sequence["fixture"]} {arm}: {field} differs')
            if sum(money(stage['known_allowance_usd']) for stage in stages) != money(total['known_allowance_usd']):
                raise ValueError('Workflow stage cost totals differ')
            if not all(stage['accepted'] for stage in stages):
                raise ValueError('Workflow diagram requires all planned changes accepted')
    for arm in ['without', 'with']:
        total = data['arms'][arm]
        sequences = [sequence['arms'][arm] for sequence in data['sequences']]
        for field in fields:
            if sum(sequence[field] for sequence in sequences) != total[field]:
                raise ValueError(f'Workflow {arm}: {field} differs')
        if sum(money(sequence['known_allowance_usd']) for sequence in sequences) != money(total['known_allowance_usd']):
            raise ValueError('Workflow sequence cost totals differ')
        for item in [total, *sequences]:
            if (item['allowance_usd'] is None) != (item['unknown_usage_requests'] > 0):
                raise ValueError('Unknown provider usage must not become a zero or exact total')
            if item['allowance_usd'] is not None and money(item['allowance_usd']) != money(item['known_allowance_usd']):
                raise ValueError('Exact and known workflow cost differ')
        if total['accepted'] != 6:
            raise ValueError('Workflow requires six accepted changes per mode')
    if any(arm['unknown_usage_requests'] for arm in data['arms'].values()) and data['overall_savings_claim'] is not None:
        raise ValueError('Incomplete billing cannot support an exact overall savings claim')
    return data


def workflows():
    data = load_workflow()
    bugs = data['sequences'][0]
    values = [money(bugs['arms'][arm]['allowance_usd']) for arm in ['without', 'with']]
    saving = (1 - values[1] / values[0]) * 100
    meta = 'Compound 0.16.7 · DeepSeek V4.1 Flash · Y Harness · 2–3 November 2026'
    description = (f'Three consecutive fixes on invoicekit, preserving code and conversation history. '
                   f'Without Compound ${values[0]}, with Compound ${values[1]} Go allowance, '
                   f'{saving:.1f}% less. Both modes accepted 3/3 changes without repair. '
                   'One sequence per mode on a previously used synthetic Python fixture; no long-term savings claim.')
    chart = Canvas(966, f'Three fixes. {saving:.1f}% less allowance.', 'COMPLETED WORKFLOW', description, meta.replace('2–3 November', '2 November'))
    chart.card(24, 158, 992, 252)
    chart.pair(197, values, [f'${value:.8f}' for value in values], max(values) * Decimal('1.08'))
    chart.text(52, 390, 'Refund allocation → leap-year proration → December invoice dates', 16, 'muted')
    chart.card(24, 430, 992, 318)
    chart.text(52, 470, 'Cumulative allowance', 22, weight=700)
    for x, color, label in [(555, 'baseline', 'Without Compound'), (795, 'green', 'With Compound')]:
        chart.rect(x, 457, 10, 10, color, 5)
        chart.text(x + 18, 468, label, 15)
    upper = (max(values) * Decimal('1.15') / Decimal('.001')).to_integral_value(rounding='ROUND_CEILING') * Decimal('.001')
    for fraction in [Decimal(0), Decimal('.5'), Decimal(1)]:
        y = 690 - float(fraction) * 170
        element('line', chart.group, x1=225, x2=930, y1=y, y2=y, stroke=THEME['line'])
        chart.text(151, y + 5, f'${upper * fraction:.3f}', 14, 'muted')
    xs = [225, 455, 685, 915]
    for arm, color in [('without', 'baseline'), ('with', 'green')]:
        cumulative = [Decimal(0)]
        for stage in bugs['stages']:
            cumulative.append(cumulative[-1] + money(stage[arm]['known_allowance_usd']))
        points = [(x, 690 - float(value / upper) * 170) for x, value in zip(xs, cumulative)]
        element('polyline', chart.group, points=' '.join(f'{x},{y:.3f}' for x, y in points),
                fill='none', stroke=THEME[color], stroke_width=3)
        for x, y in points:
            element('circle', chart.group, cx=x, cy=f'{y:.3f}', r=5, fill=THEME[color])
    for x, label in zip([207, 431, 653, 873], ['Start', 'Refund', 'Leap year', 'December']):
        chart.text(x, 722, label, 14, 'muted')
    chart.card(24, 768, 992, 130)
    requests = ' / '.join(str(bugs['arms'][arm]['requests']) for arm in ['without', 'with'])
    for x, value, label in [(52, '3/3 each', 'changes accepted'), (390, requests, 'model requests · without / with'), (750, '0 / 0', 'repair turns · without / with')]:
        chart.text(x, 819, value, 30, 'green' if x == 52 else 'ink', 750)
        chart.text(x, 858, label, 14, 'muted')
    chart.text(52, 934, 'One sequence per mode · previously used synthetic fixture · provider caches not reset.', 15, 'muted')
    yield 'benchmark-workflow-bugs.svg', chart.svg()

    arms = [data['arms'][arm] for arm in ['without', 'with']]
    desc = ('Six changes per mode across two persistent three-change workflows. All final cumulative '
            'hidden checks and original/final suites pass. Failed attempts, repairs and provider recovery '
            'requests are included. Some provider responses have unreported usage; no exact overall savings claim.')
    chart = Canvas(880, 'Six changes completed, including repairs', 'COMPLETED WORKFLOW', desc, meta)
    chart.card(24, 158, 992, 262)
    chart.text(52, 200, 'Recorded Go allowance', 22, weight=700)
    for x, arm, label, color in zip([52, 550], arms, ['Without Compound', 'With Compound'], ['ink', 'green']):
        chart.text(x, 246, label, 18, weight=600)
        prefix = '≥ ' if arm['unknown_usage_requests'] else ''
        chart.text(x, 300, prefix + f"${money(arm['known_allowance_usd']):.8f}", 33, color, 750)
        caption = f"{arm['unknown_usage_requests']} response with unreported cost" if arm['unknown_usage_requests'] else 'Complete provider usage received'
        chart.text(x, 338, caption, 15, 'muted')
    chart.text(52, 386, 'Amounts with ≥ are known minimums. Unreported usage prevents an exact overall cost ratio.', 15, 'muted')
    chart.card(24, 440, 992, 324)
    chart.text(52, 483, 'Outcome after all attempts', 21, weight=700)
    chart.text(615, 482, 'Without Compound', 16, 'muted', 600)
    chart.text(825, 482, 'With Compound', 16, 'green', 600)
    rows = [('Changes accepted', '6/6', '6/6'),
            ('Final hidden checks + original/final suites', 'All pass', 'All pass'),
            ('Original tests removed or weakened', '0', '0'),
            ('Semantic repair turns', *(arm['semantic_repairs'] for arm in arms)),
            ('Provider recovery turns', *(arm['transport_resumes'] for arm in arms)),
            ('Model requests, including failed attempts', *(arm['requests'] for arm in arms))]
    for i, (label, before, after) in enumerate(rows):
        y = 529 + i * 38
        chart.text(52, y, label, 17)
        chart.text(650, y, before, 20, weight=650)
        chart.text(870, y, after, 20, 'green', 650)
    chart.text(52, 804, 'Two repositories · one sequence per mode/repository · code and conversation persist.', 15, 'muted')
    chart.text(52, 836, 'Resumed after a provider outage. These runs do not establish universal or long-term savings.', 15, 'muted')
    yield 'benchmark-workflow-complete.svg', chart.svg()


def comparisons():
    """Two-arm summaries of saved measurements; retain all historical controls."""
    data = json.loads((SOURCES / 'comparisons.json').read_text())
    for item in data['charts']:
        source = json.loads((SOURCES / 'scenes' / (item['scene'] + '.json')).read_text())
        observed = hashlib.sha256(source['description'].encode()).hexdigest()
        if observed != item['source_description_sha256']:
            raise ValueError('Historical source changed; recheck the two-arm transcription')
        if 'values' in item:
            without, with_compound = item['values']
            desc = (f'Without Compound {without}%, with Compound {with_compound}% of changed source files '
                    'found in the top four. Same 240 held-out commits. ' + ' '.join(item['notes']))
            chart = Canvas(560, item['title'], 'WITHOUT / WITH', desc, item['subtitle'])
            chart.card(24, 158, 992, 245)
            chart.pair(202, [money(without), money(with_compound)],
                       [f'{without}%', f'{with_compound}%'], money(100),
                       label='Changed source files in top 4 · higher is better')
            for j, line in enumerate(item['notes']):
                chart.text(52, 442 + j * 31, line, 14, 'muted')
        else:
            rows = item['rows']
            desc = item['subtitle'] + '. '
            for row in rows:
                desc += row['label'] + ': ' + '; '.join(
                    f"{m['name']} without {m['without']}, with {m['with_compound']}{row['unit']}"
                    for m in row['models']) + '. '
            desc += ' '.join(item['notes'])
            chart = Canvas(158 + 186 * len(rows) + 110, item['title'], 'WITHOUT / WITH', desc, item['subtitle'])
            for i, row in enumerate(rows):
                y = 158 + i * 186
                chart.card(24, y, 992, 168)
                chart.text(52, y + 34, row['label'], 18, weight=700)
                for x, model in zip([52, 550], row['models']):
                    chart.text(x, y + 64, model['name'], 14, 'muted', 600)
                    for j, (key, label, color) in enumerate([
                            ('without', 'Without Compound', 'baseline'),
                            ('with_compound', 'With Compound', 'green')]):
                        ry = y + 83 + j * 38
                        chart.text(x, ry + 18, label, 13, weight=550)
                        chart.rect(x + 153, ry, 205, 24, 'background_secondary', 12)
                        value = model[key]
                        chart.rect(x + 153, ry, 205 * value / row['maximum'], 24, color, 12)
                        chart.text(x + 374, ry + 19, f"{value:g}{row['unit']}", 18,
                                   'ink' if j == 0 else 'green', 700)
            for j, line in enumerate(item['notes']):
                chart.text(52, 158 + 186 * len(rows) + 24 + j * 29, line, 14, 'muted')
        yield item['asset'], chart.svg()


def two_change_comparison(source):
    """Render a matched comparison after independently reconciling its saved attempts."""
    data = json.loads(source.read_text())
    fixtures = {
        'compound-dispatch-comparison-1': (
            'dispatch', 'Dispatchkit', 'dispatchkit', 'synthetic',
            (('encoded-route-bug', 'Webhook routing bug'), ('share-event-packaging', 'Event-envelope refactor')),
        ),
        'compound-flask-sequence-comparison-1': (
            'flask', 'Flask', 'flask-ipv6-session', 'upstream Flask',
            (('flask-ipv6-session', 'IPv6 test-client session'), ('flask-ipv6-run', 'IPv6 development-server parsing')),
        ),
        'compound-pstack-flask-sequence-comparison-1': (
            'pstack-flask', 'Flask', 'flask-ipv6-session', 'upstream Flask',
            (('flask-ipv6-session', 'IPv6 test-client session'), ('flask-ipv6-run', 'IPv6 development-server parsing')),
        ),
    }
    layout = fixtures.get(data['schema'])
    if layout is None or data['provider'] != 'opencode-go':
        raise ValueError('Unsupported two-change comparison')
    asset, workload, fixture, scope, labels = layout
    pstack = asset == 'pstack-flask'
    expected_model = 'qwen3.8-flash' if pstack else 'deepseek-v4.1-flash'
    if data['model'] != expected_model:
        raise ValueError('Unsupported two-change comparison model')
    plan = {key: data[key] for key in ('sequences', 'schedule')}
    if len(plan['sequences']) != 1:
        raise ValueError('Expected one matched sequence')
    sequence = plan['sequences'][0]
    if sequence['fixture'] != fixture or [task['name'] for task in sequence['tasks']] != [name for name, _ in labels]:
        raise ValueError(f'{workload} chart does not match its frozen tasks')
    attempts = data['attempts']
    summary = data['summary']
    verified = evaluate(plan, ({**attempt, 'known_costs': attempt['costs']} for attempt in attempts))
    if not verified['claim'] or any(summary[key] != verified[key] for key in (
        'valid', 'complete', 'claim', 'compound_cheaper', 'errors',
    )):
        raise ValueError(f'{workload} chart requires both tasks accepted in both modes with verified lower Compound costs')
    if any(type(attempt['requests']) is not int or attempt['requests'] < 1 for attempt in attempts):
        raise ValueError(f'{workload} chart requires a positive request count for every attempt')
    arms = []
    for mode in ('without', 'with'):
        arm = summary['arms'][mode]
        requests = sum(attempt['requests'] for attempt in attempts if attempt['arm'] == mode)
        if arm['requests'] != requests or any(arm[key] != value for key, value in verified['arms'][mode].items()):
            raise ValueError(f'{workload} {mode}: attempts differ from saved stage or arm totals')
        arms.append(arm)
    cost = [money(arm['totals']['allowance']) for arm in arms]
    reduction = (1 - cost[1] / cost[0]) * 100
    desc = (f'{workload} matched pilot. Go allowance was ${cost[0]} without and ${cost[1]} with Compound, '
            f'{reduction:.1f}% less. Both modes finished both tasks. All attempts and repairs included.')
    subtitle = (f"Compound {data['compound_version']} · DeepSeek V4.1 Flash through Y Harness"
                ' · one sequence per mode')
    modes = ('Without Compound', 'With Compound')
    request_order = 'without / with'
    if pstack:
        modes = ('pstack', 'Compound')
        request_order = 'pstack / Compound'
        desc = (f'Flask comparison. Go allowance was ${cost[0]} with pstack and ${cost[1]} with Compound, '
                f'{reduction:.1f}% less. Both passed both fixes. All attempts and repairs included.')
        subtitle = 'Claude Code 2.1.312 · Qwen3.8 Flash · one sequence per plugin'
    heading = 'Two Flask fixes' if pstack else 'Two changes'
    precision = 5 if pstack else 8
    chart = Canvas(958, f'{heading}, {reduction:.1f}% less allowance', 'MEASURED PILOT', desc, subtitle)
    chart.card(24, 157, 992, 251)
    maximum = max(cost) * Decimal('1.08')
    chart.pair(196, cost, [f'${value:.{precision}f}' for value in cost], maximum, modes=modes)
    chart.text(52, 387, f"2/2 accepted in each mode · {arms[0]['requests']} / {arms[1]['requests']} model requests {request_order}", 16, 'muted')
    for stage, label in enumerate(label for _, label in labels):
        y = 428 + stage * 226
        chart.card(24, y, 992, 206)
        values = [money(arm['by_stage'][str(stage)]['totals']['allowance']) for arm in arms]
        chart.pair(y + 34, values, [f'${v:.{precision}f}' for v in values], maximum, label, modes)
    chart.text(52, 910, 'The same repository and conversation carry forward within each mode.', 17, weight=650)
    chart.text(52, 937, f'One {scope} sequence per mode. All bars use the same allowance scale.', 15, 'muted')
    version = data['compound_version'].replace('.', '')
    return f'benchmark-{asset}-v{version}.svg', chart.svg()


def codex_attempt_usage(attempts, receipts):
    """Verify native token counts and sum all attempts in each mode."""
    for attempt in attempts:
        usage = attempt['usage']
        if (type(attempt['requests']) is not int or attempt['requests'] < 1
                or any(type(value) is not int or value < 0 for value in usage.values())
                or usage['cached_input_tokens'] > usage['input_tokens']
                or usage['total_tokens'] != usage['input_tokens'] + usage['output_tokens']
                or usage['total_tokens'] == 0):
            raise ValueError('Invalid Codex attempt usage')
    modes = ('without', 'with')
    requests = [sum(a['requests'] for a in attempts if a['mode'] == mode) for mode in modes]
    if sum(requests) != receipts:
        raise ValueError('Codex receipts do not match attempt totals')
    return requests, [sum(a['usage']['total_tokens'] for a in attempts if a['mode'] == mode) for mode in modes]


def codex_flask_comparison(source):
    """Render token usage from the four native Codex attempts."""
    data = json.loads(source.read_text())
    tasks = ('flask-ipv6-session', 'flask-ipv6-run')
    modes = ('without', 'with')
    attempts = data['attempts']
    order = [('without', 0, 0), ('with', 0, 0), ('with', 1, 0), ('without', 1, 0)]
    if (data['schema'] != 'compound-codex-flask-token-comparison-1'
            or data['model'] != 'gpt-6-luna'
            or tuple(task['name'] for task in data['tasks']) != tasks
            or [(a['mode'], a['stage'], a['attempt']) for a in attempts] != order
            or data['conversation_and_checkout_carry_forward'] is not True):
        raise ValueError('Expected the pinned, cumulative Codex Flask comparison')
    for attempt in attempts:
        grade, stage = attempt['grade'], attempt['stage']
        if (attempt['accepted'] is not True
                or grade['hidden_checks'] != dict.fromkeys(tasks[:stage + 1], 'pass')
                or grade['retained_suites_passed'] is not True
                or grade['final_tests'] != 492 + stage or grade['regression_witnesses'] < 1):
            raise ValueError('Codex Flask chart requires every fix and retained test suite to pass')
    requests, totals = codex_attempt_usage(attempts, data['native_receipts'])
    by_stage = {(a['stage'], a['mode']): a['usage']['total_tokens'] for a in attempts}
    if totals[1] >= totals[0]:
        raise ValueError('Codex Flask chart requires lower total token usage with Compound')
    reduction = (1 - totals[1] / totals[0]) * 100
    description = (f'Without Compound {totals[0]:,} tokens. With Compound {totals[1]:,} tokens. '
                   f'{reduction:.1f}% fewer total tokens. Both modes passed 2/2 fixes and 493 final tests. '
                   f'Model requests without and with were {requests[0]} and {requests[1]}. Zero repairs.')
    chart = Canvas(921, f'Two Flask fixes, {reduction:.1f}% fewer tokens', 'MATCHED CODEX RUN',
                   description, 'Codex GPT-6 Luna · One cumulative sequence per mode · Flask 514fc6b')
    maximum = max(totals) * 1.08
    chart.card(24, 157, 992, 234)
    chart.pair(196, totals, [f'{n:,}' for n in totals], maximum, 'Total tokens · lower is better')
    chart.text(52, 371, f'2/2 fixes passed in both modes · {requests[0]} / {requests[1]} requests without / with · 0 repairs', 16, 'muted')
    for stage, label in enumerate(('IPv6 test-client session', 'IPv6 development-server parsing')):
        y = 411 + stage * 222
        chart.card(24, y, 992, 202)
        values = [by_stage[stage, mode] for mode in modes]
        chart.pair(y + 37, values, [f'{n:,}' for n in values], maximum, label)
    chart.text(52, 873, 'Both final artifacts passed 493 tests. All four attempts are included.', 17, weight=650)
    chart.text(52, 899, 'Total tokens include cached input and output. All bars use the same scale.', 15, 'muted')
    return 'benchmark-flask-codex-luna.svg', chart.svg()


def codex_citation_comparison(source):
    """Render the bounded Python lookup comparison with both control repairs."""
    data = json.loads(source.read_text())
    tasks = data['tasks']
    attempts = data['attempts']
    order = [('without', 0, 0), ('without', 0, 1), ('with', 0, 0),
             ('with', 1, 0), ('without', 1, 0), ('without', 1, 1)]
    if (data['schema'] != 'compound-codex-python-citations-1' or data['model'] != 'gpt-6-luna'
            or [(t['name'], t['citations_expected']) for t in tasks] != [('flask-streaming', 3), ('django-disconnect', 4)]
            or [(a['mode'], a['stage'], a['attempt']) for a in attempts] != order
            or data['fresh_session_per_task_and_mode'] is not True
            or any(t['all_final_cited_lines_seen_in_lookup'] is not True for t in tasks)):
        raise ValueError('Expected the complete Codex Python citation comparison')
    final = {}
    for a in attempts:
        checks = a['citations_correct']
        if (len(checks) != tasks[a['stage']]['citations_expected'] or any(type(c) is not bool for c in checks)
                or a['accepted'] is not all(checks) or a['lookup_successes'] < 1):
            raise ValueError('Invalid Codex citation grade or missing lookup')
        key = a['mode'], a['stage']
        if key in final and final[key]['accepted']:
            raise ValueError('Codex citation repair follows an accepted attempt')
        final[key] = a
    requests, totals = codex_attempt_usage(attempts, data['native_receipts'])
    citations = [sum(sum(final[mode, stage]['citations_correct']) for stage in range(2)) for mode in ('without', 'with')]
    passed = [sum(final[mode, stage]['accepted'] for stage in range(2)) for mode in ('without', 'with')]
    if totals[1] >= totals[0] or passed[1] != 2:
        raise ValueError('Codex citation chart requires both Compound tasks to pass with lower total usage')
    reduction = (1 - totals[1] / totals[0]) * 100
    description = (f'Without Compound lookup {totals[0]:,} tokens and {citations[0]}/7 correct citations. '
                   f'With Compound lookup {totals[1]:,} tokens and {citations[1]}/7 correct citations. '
                   'All six attempts include two control repairs. Total tokens include cached input.')
    chart = Canvas(682, f'Python citations, {reduction:.1f}% fewer tokens', 'MATCHED CODEX RUN', description,
                   'Codex GPT-6 Luna · Flask streaming and Django disconnect · one pair per task')
    labels = ('Without Compound lookup', 'With Compound lookup')
    chart.card(24, 157, 992, 228)
    chart.pair(196, totals, [f'{n:,}' for n in totals], max(totals) * 1.08,
               'Total tokens · lower is better', labels)
    chart.text(52, 365, f'{requests[0]} / {requests[1]} model requests without / with · 2 / 0 repairs', 16, 'muted')
    chart.card(24, 405, 992, 211)
    chart.pair(444, citations, [f'{n}/7' for n in citations], 7, 'Correct final citations · higher is better', labels)
    chart.text(52, 596, f'{passed[0]}/2 tasks passed without the lookup · {passed[1]}/2 with the lookup', 16, 'muted')
    chart.text(52, 648, 'Both modes received numbered excerpts. Compound also supplied the enclosing Python symbol.', 15, 'muted')
    chart.text(52, 669, 'Totals include all attempts, repairs, cached input and output.', 15, 'muted')
    return 'benchmark-python-citations-codex-luna.svg', chart.svg()


def navigation_comparison(source):
    """Render source-graded navigation only when the matched cost ledger qualifies."""
    data = json.loads(source.read_text())
    labels = (
        ('django-disconnect', 'Django · ASGI disconnect', 4),
        ('django-row-locks', 'Django · Row locks', 3),
        ('flask-streaming', 'Flask · Streaming request context', 3),
    )
    if (data['schema'] != 'compound-map-navigation-live-1' or data['provider'] != 'opencode-go'
            or data['model'] != 'deepseek-v4.1-flash'
            or [task['id'] for task in data['tasks']] != [case[0] for case in labels]):
        raise ValueError('Unsupported navigation comparison')
    plan = {'sequences': [{'tasks': [{'name': case[0]} for case in labels]}],
            'schedule': data['schedule'], 'plan_sha256': data['plan_sha256']}
    attempts = data['attempts']
    summary = data['summary']
    verified = evaluate(plan, ({**attempt, 'known_costs': attempt['costs']} for attempt in attempts))
    if not verified['claim'] or any(summary[key] != verified[key] for key in (
        'valid', 'complete', 'claim', 'compound_cheaper', 'errors',
    )):
        raise ValueError('Navigation chart requires lower Compound costs and every task accepted in both modes')
    for attempt in attempts:
        checks = attempt['grade']['checks']
        if (type(attempt['started']) is not int or attempt['started'] < 1 or attempt['started'] != attempt['completed']
                or len(checks) != labels[attempt['stage']][2] or any(type(check) is not bool for check in checks)
                or all(checks) != attempt['grade']['success']):
            raise ValueError('Navigation attempt counts or source grades do not match the ledger')
    for stage in range(len(labels)):
        pair = [attempt for attempt in attempts if attempt['stage'] == stage and attempt['attempt'] == 0]
        hashes = {attempt['request_context_sha256'] for attempt in pair}
        if len(hashes) != 1 or not isinstance(pair[0]['request_context_sha256'], str) or len(pair[0]['request_context_sha256']) != 64:
            raise ValueError('Navigation requires matched request context outside the task prompt')
    arms = []
    citations = sum(case[2] for case in labels)
    for mode in ('without', 'with'):
        arm = summary['arms'][mode]
        scoped = [attempt for attempt in attempts if attempt['arm'] == mode]
        if (any(arm[key] != value for key, value in verified['arms'][mode].items())
                or arm['requests'] != sum(attempt['started'] for attempt in scoped)
                or arm['repairs'] != sum(attempt['attempt'] == 1 for attempt in scoped)
                or arm['citations_correct'] != citations):
            raise ValueError('Navigation arm totals do not reconcile to the recorded attempts')
        arms.append(arm)

    allowance = [money(arm['totals']['allowance']) for arm in arms]
    reduction = (1 - allowance[1] / allowance[0]) * 100
    title = f'Three navigation tasks, {reduction:.1f}% less allowance'
    description = (
        f'Without Compound ${allowance[0]:.8f}. With Compound’s map ${allowance[1]:.8f}. '
        f'Both modes got {citations}/{citations} citations right. All attempts and repairs included.'
    )
    chart = Canvas(1160, title, 'MATCHED NAVIGATION', description,
                   f"Compound {data['compound_version']} · DeepSeek V4.1 Flash through Y Harness")
    chart.card(24, 158, 992, 250)
    maximum = max(allowance) * Decimal('1.08')
    chart.pair(196, allowance, [f'${value:.8f}' for value in allowance], maximum)
    chart.text(52, 384, f"{citations}/{citations} citations in both modes · {arms[0]['requests']} / {arms[1]['requests']} requests without / with", 16, 'muted')
    for stage, (_, label, _) in enumerate(labels):
        y = 428 + stage * 222
        chart.card(24, y, 992, 206)
        values = [money(arm['by_stage'][str(stage)]['totals']['allowance']) for arm in arms]
        chart.pair(y + 34, values, [f'${v:.8f}' for v in values], maximum, label)
    chart.text(52, 1110, 'Same pinned source and prompt. The treatment receives the map summary.', 17, weight=650)
    chart.text(52, 1137, 'One fresh session per task and mode. All bars use the same allowance scale.', 15, 'muted')
    version = data['compound_version'].replace('.', '')
    return f'benchmark-navigation-v{version}.svg', chart.svg()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if checked-in SVGs differ from their sources')
    parser.add_argument('--output', type=Path, default=ROOT / '.github' / 'assets')
    args = parser.parse_args()
    outputs = {p.stem + '.svg': historical(p) for p in sorted((SOURCES / 'scenes').glob('*.json'))}
    outputs.update(pilots())
    outputs.update(workflows())
    for family in ('dispatch', 'flask', 'pstack_flask'):
        outputs.update(two_change_comparison(source) for source in sorted(SOURCES.glob(f'comparison_{family}_v*.json')))
    outputs.update(navigation_comparison(source) for source in sorted(SOURCES.glob('comparison_navigation_v*.json')))
    outputs.update([codex_flask_comparison(SOURCES / 'comparison_codex_flask_luna.json')])
    outputs.update([codex_citation_comparison(SOURCES / 'comparison_codex_python_citations.json')])
    outputs.update(comparisons())
    for name in ['benchmark-heldout', 'benchmark-real16', 'map-retrieval']:
        outputs[name + '-controls.svg'] = historical(SOURCES / 'scenes' / (name + '.json'))
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
