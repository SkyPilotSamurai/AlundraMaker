/* 800809C4: built-in program D15 */
void AI_D15(struct Entity *e) {
    s32 temp_v1;
    s32 var_v0;

    temp_v1 = e->target_anim;
    if (temp_v1 == 2) {
        var_v0 = 9;
    } else {
        var_v0 = 3;
        if (temp_v1 == 1) {
            var_v0 = 0xA;
        }
    }
    e->target_anim = var_v0;
}
