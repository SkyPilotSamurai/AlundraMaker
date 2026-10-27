/* 8008213C: built-in program E22 */
void AI_E22(struct Entity *e) {
    s32 var_a1;

    var_a1 = 0xD;
    if (e->bytes[3] != 0) {
        var_a1 = 8;
    }
    destroy_entity(e, var_a1);
}
