/* 8007E820: built-in program C76 */
s32 func_8003B5E8(struct Entity *, struct Entity *); /* extern */
? func_8004A7B4(?);                                 /* extern */

void AI_C76(struct Entity *e) {
    s32 temp_v0;
    s32 temp_v1;

    if (g_ent->x_collision == e) {
        temp_v1 = e->unk274;
        if (temp_v1 >= 0x1F) {
            play_sound(0x19);
            e->target_anim = 1;
            temp_v0 = func_8003B5E8(e, g_ent);
            if (temp_v0 != -1) {
                e->target_dir = (temp_v0 + 0x10) & 0x1F;
                return;
            }
            goto block_5;
        }
        e->unk274 = (s32) (temp_v1 + 1);
        return;
    }
block_5:
    if (e->target_anim == 1) {
        func_8004A7B4(0x19);
    }
    e->unk274 = 0;
    e->target_anim = 0;
}
