#!/usr/bin/env python3
"""
Analyze pants build dependency graph from a peek.json file.

Usage:
    python3 analyze_deps.py <peek.json> [changed_target ...]

If no changed targets are given, reads changed targets from stats.jsonl in same dir.
Outputs:
  - Direct changed targets
  - Total changeset size and type breakdown
  - Docker image targets triggered
  - Shortest dependency paths from changed targets to docker images
"""

import json
import os
import sys
from collections import Counter, defaultdict, deque


def load_peek(path):
    with open(path) as f:
        return json.load(f)


def build_graphs(data):
    forward = defaultdict(set)  # target -> deps
    reverse = defaultdict(set)  # target -> things that depend on it
    types = {}

    for item in data:
        addr = item["address"]
        types[addr] = item.get("target_type", "unknown")
        deps = item.get("dependencies", [])
        forward[addr] = set(deps)
        for dep in deps:
            reverse[dep].add(addr)

    return forward, reverse, types


TARGET_TYPE = "docker_image"
MAX_DEPTH = 15


def find_paths_to_type(start_targets, reverse, types):
    """BFS from changed targets upward to find shortest paths to TARGET_TYPE nodes."""
    results = []
    visited = set(start_targets)
    queue = deque([(t, [t]) for t in start_targets])

    while queue:
        node, path = queue.popleft()
        if len(path) > MAX_DEPTH:
            continue
        for dependent in reverse.get(node, []):
            if types.get(dependent) == TARGET_TYPE:
                results.append(path + [dependent])
            elif dependent not in visited:
                visited.add(dependent)
                queue.append((dependent, path + [dependent]))

    return results


def find_bottlenecks(start_targets, reverse, types):
    """Find which single targets, when changed, cause the most downstream impact."""
    # Count how many of the changeset targets each intermediate node feeds
    all_reachable = set()
    queue = deque(start_targets)
    visited = set(start_targets)
    while queue:
        node = queue.popleft()
        all_reachable.add(node)
        for dep in reverse.get(node, []):
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)

    return all_reachable


def print_summary(data, types):
    print(f"\n=== Changeset Summary ({len(data)} total targets) ===")
    for target_type, count in Counter(types.values()).most_common():
        print(f"  {target_type}: {count}")


def print_changeset_command(peek_path):
    stats_path = os.path.join(os.path.dirname(peek_path), "stats.jsonl")
    if os.path.exists(stats_path):
        print("\n(No targets specified — reading stats.jsonl for changed files)")
        with open(stats_path) as f:
            for line in f:
                command = json.loads(line).get("command", "")
                if "--changed-since" in command:
                    print(f"  Changeset command: {command}")
    print("  Pass changed targets as arguments for path analysis.")


def select_changed(explicit_targets, all_addresses):
    missing = [t for t in explicit_targets if t not in all_addresses]
    if missing:
        print(f"\nWarning: targets not found in peek.json: {missing}")
    return [t for t in explicit_targets if t in all_addresses]


def print_changed_and_images(changed, types):
    print(f"\n=== Changed Targets ({len(changed)}) ===")
    for target in changed:
        print(f"  {target} [{types.get(target, '?')}]")
    docker_targets = [a for a, t in types.items() if t == "docker_image"]
    print(f"\n=== Docker Images Triggered ({len(docker_targets)}) ===")
    for image in sorted(docker_targets):
        print(f"  {image}")


def shortest_paths(changed, reverse, types):
    """Keep the shortest path for each (changed target, docker image) pair."""
    seen = {}
    for start in changed:
        for path in find_paths_to_type([start], reverse, types):
            key = (path[0], path[-1])
            if key not in seen or len(path) < len(seen[key]):
                seen[key] = path
    return seen


def print_paths(seen, types):
    print("\n=== Dependency Paths (changed → docker_image) ===")
    for path in sorted(seen.values(), key=len)[:10]:
        print(f"\n  Chain (length {len(path)}):")
        for i, step in enumerate(path):
            print(f"{'  ' + '  ' * i}→ {step} [{types.get(step, '?')}]")
    if len(seen) > 10:
        print(f"\n  ... and {len(seen) - 10} more paths (showing shortest 10)")


def print_fanout(seen, types):
    print("\n=== High-Fanout Intermediaries ===")
    fanout = Counter(node for path in seen.values() for node in path[1:-1])
    print("  (nodes appearing in the most paths to docker images)")
    for node, count in fanout.most_common(5):
        print(f"  {count}x  {node} [{types.get(node, '?')}]")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <peek.json> [changed_target ...]")
        sys.exit(1)

    peek_path, explicit_targets = sys.argv[1], sys.argv[2:]
    data = load_peek(peek_path)
    _, reverse, types = build_graphs(data)
    print_summary(data, types)
    if not explicit_targets:
        print_changeset_command(peek_path)
        return

    changed = select_changed(explicit_targets, {item["address"] for item in data})
    if not changed:
        print("\nNo matching changed targets found.")
        return

    print_changed_and_images(changed, types)
    seen = shortest_paths(changed, reverse, types)
    print_paths(seen, types)
    print_fanout(seen, types)


if __name__ == "__main__":
    main()
