/* 80082090: built-in program E21 */
void AI_E21(struct Entity *e) {
    s32 temp_v1;
    struct Entity *temp_a0;

    temp_a0 = e->riding;
    if ((temp_a0 != NULL) && (temp_a0->sprite_index == 0x199) && (temp_a0->target_anim == 0)) {
        temp_a0->target_anim = 1;
        remove_entity(e);
    }
    temp_v1 = e->target_anim;
    if ((temp_v1 == 1) && (e->anim_done == temp_v1)) {
        destroy_entity(e, -1);
        return;
    }
    e->target_anim = 1;
    e->flags = (e->flags | 0x40) & ~0x30;
}
