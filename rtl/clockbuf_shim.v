// Simulation-only identity buffer. Never use for physical signoff.
module sky130_fd_sc_hd__clkbuf_16(input A, output X);
  assign X = A;
endmodule
// These module declarations satisfy elaboration of unused physical branches
// when FUNCTIONAL is selected; they must never be used for timing studies.
module sky130_fd_sc_hd__clkbuf_1(input A, output X); assign X=A; endmodule
module sky130_fd_sc_hd__clkbuf_2(input A, output X); assign X=A; endmodule
module sky130_fd_sc_hd__clkinv_1(input A, output Y); assign Y=~A; endmodule
module sky130_fd_sc_hd__clkinv_2(input A, output Y); assign Y=~A; endmodule
module sky130_fd_sc_hd__clkinv_8(input A, output Y); assign Y=~A; endmodule
module sky130_fd_sc_hd__einvp_1(input A, TE, output Z); assign Z=TE ? ~A : 1'bz; endmodule
module sky130_fd_sc_hd__einvp_2(input A, TE, output Z); assign Z=TE ? ~A : 1'bz; endmodule
module sky130_fd_sc_hd__einvn_4(input A, TE_B, output Z); assign Z=TE_B ? 1'bz : ~A; endmodule
module sky130_fd_sc_hd__einvn_8(input A, TE_B, output Z); assign Z=TE_B ? 1'bz : ~A; endmodule
module sky130_fd_sc_hd__conb_1(output HI, LO); assign HI=1'b1; assign LO=1'b0; endmodule
module sky130_fd_sc_hd__or2_2(input A, B, output X); assign X=A|B; endmodule
