/* 8007D778: built-in program C65 */
extern ? D_800204F0;
extern ? D_800206F0;

void AI_C65(struct Entity *e) {
    s32 temp_a1;
    s32 temp_a2;
    s32 temp_v0;
    s32 temp_v0_2;
    s32 var_t0;
    s32 var_v1;
    s32 var_v1_2;
    void **var_a3;
    void *temp_s0;

    temp_v0 = find_targets(e, 1, *e->attack_addr & 0xF, 0x80142B80, 0x80142C80);
    var_t0 = 0;
    if (temp_v0 > 0) {
        var_a3 = (void **)0x80142B80;
loop_2:
        temp_s0 = *var_a3;
        temp_a1 = temp_s0->unk114 - e->px;
        temp_a2 = temp_s0->unk118 - e->py;
        var_v1 = temp_a1;
        if (temp_a1 < 0) {
            var_v1 = -var_v1;
        }
        if (var_v1 <= 0x01400000) {
            var_v1_2 = temp_a2;
            if (temp_a2 < 0) {
                var_v1_2 = -var_v1_2;
            }
            var_t0 += 1;
            if (var_v1_2 <= 0xF00000) {
                temp_v0_2 = ((dir_from_delta(temp_a1, temp_a2) + 0x14) & 0x1F) * 0x10;
                temp_s0->unkCC = (s32) (*(temp_v0_2 + &D_800206F0) * 0x300);
                temp_s0->unkD0 = (s32) (*(&D_800204F0 + temp_v0_2) << 9);
                return;
            }
            goto block_10;
        }
        var_t0 += 1;
block_10:
        var_a3 += 4;
        if (var_t0 >= temp_v0) {

        } else {
            goto loop_2;
        }
    }
}
