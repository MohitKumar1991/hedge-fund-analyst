import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';
import { PLUGINS_DIR } from './paths.js';
import { getSkills, skillByName } from './registry.js';

// Walk the `requires` graph from one or more roots and return the full set of
// skills to install (dependencies included), ordered dependencies-first.
// Throws on an unknown skill or a dependency cycle.
export function resolveClosure(rootNames, skills = getSkills()) {
  const ordered = [];
  const seen = new Set();
  const inStack = new Set();

  const visit = (name, trail) => {
    const skill = skillByName(name, skills);
    if (!skill) {
      throw new Error(`unknown skill "${name}"${trail.length ? ` (required by ${trail[trail.length - 1]})` : ''}`);
    }
    if (seen.has(skill.name)) return;
    if (inStack.has(skill.name)) {
      throw new Error(`dependency cycle: ${[...trail, skill.name].join(' → ')}`);
    }
    inStack.add(skill.name);
    for (const dep of skill.requires) visit(dep, [...trail, skill.name]);
    inStack.delete(skill.name);
    seen.add(skill.name);
    ordered.push(skill);
  };

  for (const name of rootNames) visit(name, []);
  return ordered;
}

// One walk of plugins/, shared by the CLI (personas) and the validator: each
// plugin's manifest state plus both places its skills can be declared — a
// manifest `skills` array (legacy) or folders bundled under <plugin>/skills/
// (the self-contained marketplace layout).
export function scanPlugins() {
  if (!existsSync(PLUGINS_DIR)) return [];
  const out = [];
  for (const entry of readdirSync(PLUGINS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const dir = join(PLUGINS_DIR, entry.name);
    const manifestPath = join(dir, '.claude-plugin', 'plugin.json');
    let manifest = null;
    let manifestError = null;
    if (!existsSync(manifestPath)) {
      manifestError = 'missing .claude-plugin/plugin.json';
    } else {
      try { manifest = JSON.parse(readFileSync(manifestPath, 'utf8')); }
      catch (e) { manifestError = `invalid JSON: ${e.message}`; }
    }
    const bundleDir = join(dir, 'skills');
    const bundledSkills = existsSync(bundleDir)
      ? readdirSync(bundleDir, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .map((e) => e.name)
      : [];
    out.push({
      folder: entry.name,
      dir,
      manifest,
      manifestError,
      manifestSkillPaths: (manifest && manifest.skills) || [],
      bundledSkills,
    });
  }
  return out;
}

// Personas are defined by the plugin manifests under plugins/ (single source of
// truth). A self-contained plugin carries its skills as bundled folders rather
// than a manifest `skills` array, so fall back to the bundle when no explicit
// list is present.
export function listPersonas() {
  const out = [];
  for (const p of scanPlugins()) {
    if (!p.manifest) continue;
    let skills = p.manifestSkillPaths.map((x) => basename(x));
    if (!skills.length) skills = p.bundledSkills;
    out.push({
      name: p.manifest.name || p.folder,
      description: p.manifest.description || '',
      skills,
    });
  }
  return out;
}

export function personaByName(name) {
  return listPersonas().find((p) => p.name === name) || null;
}

// Resolve a target into a closure. `all` installs every shipped skill; otherwise
// the target may be a persona name or a single skill name.
export function resolveTarget(name, skills = getSkills()) {
  if (name === 'all') return resolveClosure(skills.map((s) => s.name), skills);
  const persona = personaByName(name);
  if (persona) return resolveClosure(persona.skills, skills);
  return resolveClosure([name], skills);
}
