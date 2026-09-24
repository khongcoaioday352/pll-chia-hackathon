`timescale 1ns/1ps

module tb_digital_pll;
    reg resetb, enable, osc, dco;
    reg [4:0] div;
    reg [25:0] ext_trim;
    wire [1:0] clockp;
    integer i, f_jitter, wait_cnt, stable_cnt, d, dither_transitions, dither_min, dither_max;
    reg [25:0] prev_otrim, saved_otrim;
    real freq, lock_start, lock_end, lock_time, f_target, lock_time_step;
    time t_jitter_prev, t_jitter_curr;
    reg locked;
    reg jitter_enable;
    integer jitter_seed, jitter_fd;

    digital_pll dut (
        .resetb(resetb), .enable(enable), .osc(osc),
        .clockp(clockp), .div(div), .dco(dco), .ext_trim(ext_trim)
    );

`ifndef GATESIM
    wire [25:0] otrim = dut.pll_control.trim;
`endif

    // Dual-mode clock generator: clean 10 MHz or jittered
    always begin
        if (jitter_enable) begin
            #(50 + (($random(jitter_seed) % 5) * 0.1));
            osc = ~osc;
        end else begin
            #50 osc = ~osc;
        end
    end

    task measure_freq;
        real t0, t1;
        begin
            @(posedge clockp[0]); t0 = $realtime;
            @(posedge clockp[0]); t1 = $realtime;
            freq = (t1 > t0) ? 1000.0 / (t1 - t0) : 0;
        end
    endtask

    task wait_for_lock;
        output reg locked;
        output real lock_time;
        integer wc;
        begin
            lock_start = $realtime;
`ifndef GATESIM
            locked = 0; stable_cnt = 0; prev_otrim = ~otrim;
            for (wc = 0; wc < 50 && !locked; wc = wc + 1) begin
                @(posedge osc);
                if (otrim === prev_otrim) begin
                    stable_cnt = stable_cnt + 1;
                    if (stable_cnt >= 5) locked = 1;
                end else begin
                    stable_cnt = 0;
                    prev_otrim = otrim;
                end
            end
`else
            repeat (50) @(posedge osc);
            locked = 1;
`endif
            lock_time = ($realtime - lock_start) / 1000.0;
        end
    endtask

    initial begin
        $dumpfile("tb_digital_pll.vcd");
        $dumpvars(0, tb_digital_pll);

        jitter_enable = 0; jitter_seed = 42;
        resetb = 0; enable = 0; osc = 0;
        dco = 0; ext_trim = 26'd0; div = 5'd8;
        #160; resetb = 1; enable = 1;

        // ---------------------------------------------------------------
        // Test 1: DCO mode — sweep ext_trim
        // ---------------------------------------------------------------
        $display("=== Test 1: DCO mode ===");
        dco = 1; resetb = 0; #100; resetb = 1; #200;
        for (i = 0; i < 26; i = i + 1) begin
            ext_trim[i] = 1'b1; #1000;
            measure_freq;
            $display("ext_trim[%0d]=1: %0.3f MHz", i, freq);
        end

        // ---------------------------------------------------------------
        // Test 2: Lock-in time, div sweep 17..22
        // ---------------------------------------------------------------
        $display("\n=== Test 2: Lock-in time ===");
        dco = 0;
        for (d = 18; d <= 22; d = d + 1) begin div = d;
	   enable = 0; resetb = 0; #50;
           enable = 1; resetb = 1; #1;
           wait_for_lock(locked, lock_time);
            f_target = 10.0 * div;
            if (!locked) begin
                $display("div=%d: TIMEOUT", div);
            end else begin
                measure_freq;
                if (freq >= f_target * 0.98 && freq <= f_target * 1.02)
                    $display("div=%d: PASS locked in %0.2f us, freq=%0.2f MHz (target=%0.2f)", div, lock_time, freq, f_target);
                else
                    $display("div=%d: FAIL freq=%0.2f MHz, target=%0.2f MHz", div, freq, f_target);
            end
        end

        // ---------------------------------------------------------------
        // Test 3: Reset by resetb and enable
        // ---------------------------------------------------------------
        $display("=== Test 3: Reset ===");
        enable = 0; resetb = 0; #50; enable = 1; resetb = 1; #200;
        measure_freq;
        if (freq > 0) $display("PASS: resetb release, freq=%0.3f MHz", freq);
        else          $display("FAIL: no oscillation after resetb release");

        enable = 0; #50; enable = 1; #200;
        measure_freq;
        if (freq > 0) $display("PASS: enable release, freq=%0.3f MHz", freq);
        else          $display("FAIL: no oscillation after enable release");

        // ---------------------------------------------------------------
        // Test 4: Jitter measurement (1ms run)
        // ---------------------------------------------------------------
        $display("=== Test 4: Jitter (1ms run) ===");
        f_jitter = $fopen("jitter_log.txt", "w");
        enable = 0; resetb = 0; #50; enable = 1; resetb = 1;
        repeat (2) @(posedge clockp[0]);
        for (i = 0; i < 100000; i = i + 1) begin
            @(posedge clockp[0]); t_jitter_prev = $time;
            @(posedge clockp[0]); t_jitter_curr = $time;
            $fdisplay(f_jitter, "%0t", t_jitter_curr - t_jitter_prev);
        end
        $fclose(f_jitter);

        // ---------------------------------------------------------------
        // Test 5: Step response (div change on-the-fly)
        // ---------------------------------------------------------------
        $display("\n=== Test 5: Step response ===");
        enable = 0; resetb = 0; #50;
        div = 5'd20; enable = 1; resetb = 1; #1;
        wait_for_lock(locked, lock_time);
        if (locked) begin
            measure_freq;
            $display("Locked to div=%d: %0.2f MHz (target=%0.2f) in %0.2f us",
                div, freq, 10.0*div, lock_time);
        end
        // Step to div=12 (lower target — controller must increase delay)
        div = 5'd12;
        wait_for_lock(locked, lock_time_step);
        if (locked) begin
            measure_freq;
            $display("Step div=20->12: locked %0.2f MHz (target=%0.2f) in %0.2f us",
                freq, 10.0*div, lock_time_step);
        end else begin
            $display("Step div=20->12: TIMEOUT");
        end
        // Step back to div=20 (higher target — controller must decrease delay)
        div = 5'd20;
        wait_for_lock(locked, lock_time_step);
        if (locked) begin
            measure_freq;
            $display("Step div=12->20: locked %0.2f MHz (target=%0.2f) in %0.2f us",
                freq, 10.0*div, lock_time_step);
        end else begin
            $display("Step div=12->20: TIMEOUT");
        end

        // ---------------------------------------------------------------
        // Test 6: Full div range sweep (0..31)
        // ---------------------------------------------------------------
        $display("\n=== Test 6: Full div sweep ===");
        for (d = 0; d <= 31; d = d + 1) begin div = d;
            enable = 0; resetb = 0; #50;
            enable = 1; resetb = 1; #1;
            wait_for_lock(locked, lock_time);
            f_target = 10.0 * div;
            if (!locked) begin
                $display("div=%2d: TIMEOUT", div);
            end else begin
                measure_freq;
                if (freq >= f_target * 0.98 && freq <= f_target * 1.02)
                    $display("div=%2d: PASS  lock=%0.2fus  freq=%0.2f (target=%0.2f)",
                        div, lock_time, freq, f_target);
                else
                    $display("div=%2d: FAIL  freq=%0.2f (target=%0.2f)",
                        div, freq, f_target);
            end
        end

        // ---------------------------------------------------------------
        // Test 7: Steady-state dithering
        // ---------------------------------------------------------------
        $display("\n=== Test 7: Steady-state dithering ===");
        enable = 0; resetb = 0; #50;
        div = 5'd19; enable = 1; resetb = 1; #1;
        wait_for_lock(locked, lock_time);
        if (locked) begin
`ifndef GATESIM
            dither_transitions = 0; saved_otrim = otrim;
            dither_min = 127; dither_max = 0;
            for (d = 0; d < 1000; d = d + 1) begin
                @(posedge osc);
                if (otrim !== saved_otrim) begin
                    dither_transitions = dither_transitions + 1;
                    saved_otrim = otrim;
                end
                if (dut.pll_control.tval < dither_min)
                    dither_min = dut.pll_control.tval;
                if (dut.pll_control.tval > dither_max)
                    dither_max = dut.pll_control.tval;
            end
            $display("After lock: %d otrim transitions in 1000 cycles, tval range [%d..%d]%s",
                dither_transitions, dither_min, dither_max,
                (dither_transitions == 0) ? " (fully stable)" : "");
`else
            $display("Steady-state dither: skipped in gate-level sim (no internal signals)");
`endif
        end else begin
            $display("div=19: did not lock, skipping dither test");
        end

        // ---------------------------------------------------------------
        // Test 8: Glitch tolerance
        // ---------------------------------------------------------------
        $display("\n=== Test 8: Glitch tolerance ===");
        enable = 0; resetb = 0; #50;
        div = 5'd19; enable = 1; resetb = 1; #1;
        wait_for_lock(locked, lock_time);
        if (locked) begin
            $display("Locked at div=19, injecting glitches...");
            // (a) Narrow resetb pulse while locked
            resetb = 0; #1; resetb = 1; #200;
            measure_freq;
            $display("(a) 1ns resetb pulse: freq=%0.3f MHz %s",
                freq, (freq > 0) ? "PASS" : "FAIL");
            // (b) Enable toggle for 1ns mid-lock
            enable = 0; #1; enable = 1; #200;
            measure_freq;
            $display("(b) 1ns enable toggle: freq=%0.3f MHz %s",
                freq, (freq > 0) ? "PASS" : "FAIL");
            // (c) Reset during DCO mode
            dco = 1; ext_trim = 26'd0;
            resetb = 0; #1; resetb = 1; #200;
            measure_freq;
            $display("(c) DCO mode 1ns reset: freq=%0.3f MHz %s",
                freq, (freq > 0 && freq > 200) ? "PASS" : "FAIL");
            dco = 0;
        end else begin
            $display("div=19: did not lock, skipping glitch test");
        end

        // ---------------------------------------------------------------
        // Test 9: Noise on reference
        // ---------------------------------------------------------------
        $display("\n=== Test 9: Noise on reference ===");
        jitter_fd = $fopen("noise_log.txt", "w");
        enable = 0; resetb = 0; #50;
        jitter_enable = 1;  // switch to jittered clock before starting PLL
        div = 5'd19; enable = 1; resetb = 1; #1;
        wait_for_lock(locked, lock_time);
        if (locked) begin
            measure_freq;
            $display("Locked with jittered ref: %0.3f MHz, lock=%0.2f us", freq, lock_time);
        end else begin
            $display("Locked with jittered ref: TIMEOUT");
        end
        // Log output periods for jitter analysis
        repeat (2) @(posedge clockp[0]);
        for (i = 0; i < 1000; i = i + 1) begin
            @(posedge clockp[0]); t_jitter_prev = $time;
            @(posedge clockp[0]); t_jitter_curr = $time;
            $fdisplay(jitter_fd, "%0t", t_jitter_curr - t_jitter_prev);
        end
        $fclose(jitter_fd);
        $display("Wrote noise_log.txt with 1000 output periods");
        jitter_enable = 0;

        $display("\n--- All top-level tests done ---");
        $finish;
    end
`ifdef GATESIM
    initial begin
        $sdf_annotate("digital_pll.sdf", dut);
    end
`endif

endmodule
