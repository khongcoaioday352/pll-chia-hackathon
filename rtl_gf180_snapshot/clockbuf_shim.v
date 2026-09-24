// Simulation-only declarations for cells in the unused physical oscillator
// branch. Compile with -DFUNCTIONAL. Never use this file for gate-level timing.
module gf180mcu_fd_sc_mcu7t5v0__inv_1(input I, output ZN); assign ZN=~I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__clkbuf_1(input I, output Z); assign Z=I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__clkbuf_2(input I, output Z); assign Z=I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__clkinv_1(input I, output ZN); assign ZN=~I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__clkinv_2(input I, output ZN); assign ZN=~I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__clkinv_8(input I, output ZN); assign ZN=~I; endmodule
module gf180mcu_fd_sc_mcu7t5v0__invz_1(input I, EN, output ZN); assign ZN=EN?~I:1'bz; endmodule
module gf180mcu_fd_sc_mcu7t5v0__invz_2(input I, EN, output ZN); assign ZN=EN?~I:1'bz; endmodule
module gf180mcu_fd_sc_mcu7t5v0__invz_4(input I, EN, output ZN); assign ZN=EN?~I:1'bz; endmodule
module gf180mcu_fd_sc_mcu7t5v0__invz_8(input I, EN, output ZN); assign ZN=EN?~I:1'bz; endmodule
module gf180mcu_fd_sc_mcu7t5v0__nor2_2(input A1,A2,output ZN); assign ZN=~(A1|A2); endmodule
module gf180mcu_fd_sc_mcu7t5v0__tieh(output Z); assign Z=1'b1; endmodule
