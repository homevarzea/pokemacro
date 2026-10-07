'use strict';
// PokeAlliance 2026-10-07. RVAs verified against this exact executable.
const BUILD = '5db2cf3f15ae5e92ea6843a8a80011723146068b409dda930387521d123f6e33';
const module = Process.getModuleByName('PokeAlliance_gl.exe');
const base = module.base;
const profile = {
  gettop: {rva: 0x158f9c0, bytes: '488b4128482b412048c1f803c3'},
  settop: {rva: 0x1590890, bytes: '48895c2408574883ec204863fa488bd9'},
  load: {rva: 0x1597f30, bytes: '4c8bdc49895b08574881ecf00000004d'},
  pcall: {rva: 0x158fea0, bytes: '48895c24084889742410574883ec2048'},
  tostring: {rva: 0x1590a50, bytes: '48895c24084889742410574883ec2049'}
};
// Check the running module as well as the executable hash checked by Python.
if (Process.arch !== 'x64') throw new Error('This bridge requires the verified x64 client');
for (const [name, entry] of Object.entries(profile)) {
  const actual = Array.from(new Uint8Array(base.add(entry.rva).readByteArray(entry.bytes.length / 2)))
    .map(value => value.toString(16).padStart(2, '0')).join('');
  if (actual !== entry.bytes) throw new Error('Client code changed at ' + name + '; offsets need verification');
}
// LuaJIT uses SEH for Lua errors; its own protected-call handler must catch them.
const fn = (name, result, args) => new NativeFunction(base.add(profile[name].rva), result, args, {exceptions: 'propagate'});
const gettop = fn('gettop', 'int', ['pointer']);
const settop = fn('settop', 'void', ['pointer', 'int']);
const load = fn('load', 'int', ['pointer', 'pointer', 'size_t', 'pointer', 'pointer']);
const pcall = fn('pcall', 'int', ['pointer', 'int', 'int', 'int']);
const tostring = fn('tostring', 'pointer', ['pointer', 'int', 'pointer']);
let pending = null, busy = false, observedCalls = 0, completedQueries = 0;
let lastThread = null;
// Run only when the client's own Lua protected call has returned successfully.
// This supplies lua_State* directly and avoids the obsolete LuaInterface offset.
const hook = Interceptor.attach(base.add(profile.pcall.rva), {
  onEnter(args) {
    if (!busy) {
      observedCalls++;
      lastThread = this.threadId;
    }
    this.state = !busy && pending ? args[0] : null;
  },
  onLeave(retval) {
    if (!this.state || busy || !pending || retval.toInt32() !== 0) return;
    busy = true;
    const job = pending;
    pending = null;
    clearTimeout(job.timer);
    const L = this.state;
    let top = null, result;
    try {
      top = gettop(L);
      const source = Memory.allocUtf8String(job.source);
      const name = Memory.allocUtf8String('@PkaLuaBridge');
      let status = load(L, source, job.length, name, ptr(0));
      if (status === 0) status = pcall(L, 0, 1, 0);
      const len = Memory.alloc(8);
      len.writeU64(0);
      const value = tostring(L, -1, len);
      const size = Number(len.readU64());
      if (size > 8 * 1024 * 1024) throw new Error('Lua result exceeds 8 MiB');
      const result_bytes = value.isNull() ? null : Array.from(new Uint8Array(value.readByteArray(size)));
      result = {status, result_bytes};
    } catch (error) {
      result = {bridge_error: error && error.stack ? error.stack : String(error)};
    } finally {
      try {
        if (top !== null) settop(L, top);
      } catch (error) {
        result = {bridge_error: 'Could not restore Lua stack: ' + String(error)};
      }
      busy = false;
    }
    completedQueries++;
    job.resolve(result);
  }
});
rpc.exports = {
  info() {
    return {build: BUILD, arch: Process.arch, observed_calls: observedCalls,
      completed_queries: completedQueries, last_thread: lastThread, pending: pending !== null, busy};
  },
  run(source) {
    if (pending || busy) throw new Error('A query is already pending');
    if (typeof source !== 'string') throw new Error('Lua source must be a string');
    const length = unescape(encodeURIComponent(source)).length;
    if (length > 1024 * 1024) throw new Error('Lua source exceeds 1 MiB');
    return new Promise(resolve => {
      const job = {source, length, resolve};
      job.timer = setTimeout(() => {
        if (pending === job) {
          pending = null;
          resolve({bridge_error: 'No successful client Lua call within 15 seconds'});
        }
      }, 15000);
      pending = job;
    });
  }
};
