/* 80063B1C: built-in program A15 */
void AI_A15(struct Entity *e) {
    e->unk284 = spawn_warp_entity(e, 1, 0x9D, e->px + 0x380000, /* extra? */ e->py, /* extra? */ (e->pz + 0xFFE00000), /* extra? */ e->target_dir);
    *(s32 *)0x801F0074 = 0;
}
