/* 80081720: built-in program E5 */
void AI_E5(struct Entity *e) {
    if (e->target_anim == 1) {
        if (e->anim_done == 1) {
            destroy_entity(e, -1);
        }
    } else {
        e->target_anim = 1;
        e->flags = (e->flags | 0x40) & ~0x30;
        spawn_effect(0, 8, 0, e->px, e->py, e->pz);
    }
}
