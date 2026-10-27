/* 80081658: built-in program E3 */
void AI_E3(struct Entity *e) {
    s32 temp_v1;

    temp_v1 = e->target_anim;
    if ((temp_v1 == 1) && (e->anim_done == temp_v1)) {
        destroy_entity(e, -1);
        return;
    }
    e->target_anim = 1;
    e->flags = (e->flags | 0x40) & ~0x30;
}
