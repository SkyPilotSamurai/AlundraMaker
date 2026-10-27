/* 80063A08: built-in program A11 */
void AI_A11(struct Entity *e) {
    struct Entity *temp_v0;

    temp_v0 = spawn_warp_entity(e, 1, 0xF5, e->px + 0xF00000, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir);
    e->unk284 = temp_v0;
    temp_v0->unk284 = 0;
    e->target_anim = 3;
    temp_v0->target_anim = 0;
}
