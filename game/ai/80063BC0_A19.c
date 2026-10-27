/* 80063BC0: built-in program A19 */
void AI_A19(struct Entity *e) {
    e->bytes[1] = (u8) e->prog_c;
}
