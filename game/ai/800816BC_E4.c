/* 800816BC: built-in program E4 */
void AI_E4(struct Entity *e) {
    if ((e->target_anim == 4) && (e->anim_done == 1)) {
        destroy_entity(e, -1);
        return;
    }
    e->target_anim = 4;
    e->flags = (e->flags | 0x40) & ~0x30;
}
