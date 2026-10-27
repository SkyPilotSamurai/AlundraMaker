/* 80081BCC: built-in program E13 */
void AI_E13(struct Entity *e) {
    if (e->target_anim == 1) {
        if (e->anim_done == 1) {
            destroy_entity(e, -1);
        }
    } else {
        *(s32 *)0x801B6C4C = 2;
        e->target_anim = 1;
        e->flags = (e->flags | 0x40) & ~0x30;
    }
}
