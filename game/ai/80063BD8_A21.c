/* 80063BD8: built-in program A21 */
void AI_A21(struct Entity *e) {
    spawn_warp_entity(e, 1, 0xD8, e->px, /* extra? */ e->py, /* extra? */ e->pz, /* extra? */ e->target_dir)->target_anim = 5;
    e->target_anim = 3;
    e->py += 0xFFF00000;
    e->pz += 0x300000;
}
