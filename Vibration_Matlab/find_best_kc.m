% === BASE PARAMETERS ===
M = 12.6;                % Load mass (kg)
g = 9.81;                % Gravitational acceleration (m/s^2)

% Material Properties (Brass)
G = 77.5e9;              % Shear modulus (Pa)
rho = 7955;              % Density (kg/m^3)
sigma_b = 630e6;         % Tensile yield strength (Pa)

% Target Natural Frequency
f0_vertical = 1.1;                  
k_target = M * (2 * pi * f0_vertical)^2;
L_Tower = 0.46;          % Tower height (m)

% Search Ranges
d_wire_range = 1e-3:1e-3:5e-3;      % Wire diameter (1-5mm)
d_in_range = 5e-3:1e-3:9.5e-2;      % Inner diameter (5-95mm)
d_hook_range = 1e-3:1e-3:5e-3;      % Hook diameter (1-5mm)
r_hook_range = 3e-3:1e-3:10e-3;     % Hook radius (3-10mm)

results = [];
best_freq = Inf;         
best_params = [];

for i = 1:length(d_wire_range)
    for j = 1:length(d_in_range)
        for m = 1:length(d_hook_range)
            for n = 1:length(r_hook_range)
                d_wire = d_wire_range(i);
                d_in   = d_in_range(j);
                d_hook = d_hook_range(m);
                r_hook = r_hook_range(n);

                d_out = d_in + 2 * d_wire;
                D = (d_in + d_out) / 2;
                c_index = D / d_wire;

                if d_out > 0.1
                    continue;
                end

                n_calc = (G * d_wire^4) / (8 * D^3 * k_target);
                n_eff_options = unique(round([n_calc+1.5, n_calc+2, n_calc+2.2]));

                for k = 1:length(n_eff_options)
                    n_eff = n_eff_options(k);
                    n_total = n_eff + 2;

                    k_actual = (G * d_wire^4) / (8 * D^3 * n_eff);

                    A_coil = pi * (d_wire^2 / 4);         
                    L_wire = n_eff * pi * D;              
                    m_s = rho * A_coil * L_wire;          
                    m_eq = M + (1/3) * m_s;               

                    delta_static = m_eq * g / k_actual;
                    L_eq = n_total * d_wire + delta_static + 2 * d_hook + 2 * r_hook;

                    if L_eq > 0.35
                        continue;
                    end
                    L0 = n_total * d_wire + 2 * d_hook + 2 * r_hook;
                    L = L_eq + L_Tower / 2;  

                    f0_radial = sqrt(g / L) / (2 * pi);

                    F_max = m_eq * g;
                    Kw = (4*c_index - 1)/(4*c_index - 4) + 0.615/c_index;
                    tau_e = Kw * (8 * F_max * D) / (pi * d_wire^3);

                    if tau_e > 0.45 * sigma_b 
                        continue;
                    end

                    kappa_3 = (4 * c_index^2 - c_index - 1) / (4 * c_index * (c_index - 1));
                    kappa_3_prime = kappa_3 + 1 / (4 * c_index);
                    sigma_max = kappa_3_prime * (16 * D * F_max) / (pi * d_wire^3);

                    if sigma_max >= 0.7 * sigma_b
                        continue;
                    end

                    actual_freq = sqrt(k_actual/m_eq)/(2*pi);

                    results = [results;
                        d_wire*1000, d_in*1000, d_out*1000, D*1000, ...
                        c_index, n_total, n_eff, d_wire*1000, ...
                        n_total*d_wire*1000, L_eq*1000, A_coil*1e6, ...
                        m_s, m_eq, k_actual, ...
                        actual_freq, ...
                        tau_e/1e6, f0_radial, sigma_max/1e6];

                    if actual_freq < f0_vertical && actual_freq < best_freq
                        best_freq = actual_freq;
                        best_params = [d_wire, D, n_total, n_eff, m_s, m_eq, k_actual, ...
                            actual_freq, f0_radial, sigma_max];
                    end
                end
            end
        end
    end
end
if ~isempty(results)
    % ===== DISPLAY RESULTS =====
    header = {'Wire_d_mm', 'Inner_d_mm', 'Outer_d_mm', 'Mean_D_mm', 'Index_c', ...
        'Total_turns', 'Eff_turns', 'Pitch_mm', 'Free_len_L0_mm', ...
        'Assembly_len_Leq_mm', 'Area_mm2', 'Spring_mass_kg', ...
        'Eff_mass_kg', 'Stiffness_N_m', 'Freq_Hz', ...
        'Tau_max_MPa', 'Radial_freq_Hz', 'Sigma_max_MPa'};
    
    fprintf('\n%-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-12s %-12s %-10s %-10s %-12s %-10s %-10s\n', header{:});

    for i = 1:size(results,1)
        fprintf('%-10.2f %-10.2f %-10.2f %-10.2f %-10.2f %-10d %-10d %-10.2f %-10.2f %-10.2f %-10.2f %-12.4f %-12.4f %-10.1f %-10.2f %-12.2f %-10.2f %-10.2f\n', results(i,:));
    end

    if ~isempty(best_params)
        fprintf('\n=== Optimal Spring Design (Minimum Freq: %.4f Hz) ===\n', best_freq);
        fprintf('Wire Diameter: %.1f mm\n', best_params(1)*1000);
        fprintf('Mean Diameter: %.1f mm\n', best_params(2)*1000);
        fprintf('Total Turns: %d (Effective Turns: %d)\n', best_params(3), best_params(4));
        fprintf('Spring Mass: %.4f kg\n', best_params(5));
        fprintf('Effective Mass: %.4f kg\n', best_params(6));
        fprintf('Stiffness: %.1f N/m\n', best_params(7));
        fprintf('Axial Natural Freq: %.4f Hz (Target: %.1f Hz)\n', best_params(8), f0_vertical);
        fprintf('Radial Natural Freq: %.2f Hz\n', best_params(9));
        fprintf('Max Tensile Stress: %.2f MPa (Limit: %.2f MPa)\n', best_params(10)/1e6, 0.7*sigma_b/1e6);
    end

    % ====== DAMPING OPTIMIZATION ======
    k_actual = best_params(7);   
    m_eq = best_params(6);       
    fn = best_params(8);         
    wn = 2*pi*fn;                

    c_range = linspace(0.1, 1000, 10000);  
    f_range = 0:0.1:100;         
    omega_range = 2*pi*f_range;

    best_c = 0;
    min_T_energy = Inf;          
    best_T = [];

    T_energy_values = zeros(size(c_range));
    zeta_values = zeros(size(c_range));

    C_constant = 2*sqrt(k_actual*m_eq);

    for idx = 1:length(c_range)
        c = c_range(idx);
        zeta = c / C_constant;
        zeta_values(idx) = zeta;

        T = zeros(size(omega_range));
        for j = 1:length(omega_range)
            omega = omega_range(j);
            r = omega/wn;

            numerator = sqrt(1 + (2*zeta*r)^2);
            denominator = sqrt((1 - r^2)^2 + (2*zeta*r)^2);
            T(j) = numerator / denominator;
        end

        T_energy = trapz(f_range, T.^2);
        T_energy_values(idx) = T_energy;

        if T_energy < min_T_energy
            min_T_energy = T_energy;
            min_peak_T = max(T);
            min_avg_T = mean(T);
            best_c = c;
            best_T = T;
            best_zeta = zeta;
        end
    end

    % ===== DISPLAY OPTIMAL DAMPING =====
    fprintf('\n=== Optimal Damping Parameters ===\n');
    fprintf('Best Damping Coefficient c = %.2f N·s/m\n', best_c);
    fprintf('Corresponding Damping Ratio ζ = %.4f\n', best_zeta);
    fprintf('Minimum Peak Transmission Ratio = %.4f\n', min_peak_T);
    fprintf('Minimum Avg Transmission Ratio = %.4f\n', min_avg_T);
    fprintf('Minimum Energy (0–100 Hz) = %.4f\n', min_T_energy);

    % === GLOBAL PLOT SETTINGS ===
    fontEN = 'Arial';
    set(0,'defaultAxesFontName',fontEN);
    set(0,'defaultTextFontName',fontEN);
    set(0,'defaultLegendFontName',fontEN);
    set(0,'defaultUIControlFontName',fontEN);
    set(0,'defaultAxesFontSize',12);
    set(0,'defaultTextInterpreter','none');     
    set(0,'defaultLegendInterpreter','none');   

    figSize = [1, 1, 10, 5];  % in inches
    % === Figure 1: Frequency Response Curve ===
    figure('Name', 'Transmission Ratio Curve', 'Units', 'inches', 'Position', figSize);
    semilogx(f_range, best_T, 'b-', 'LineWidth', 2);
    hold on;
    plot([fn, fn], [0, max(best_T)], 'r--', 'LineWidth', 1.5, 'DisplayName', 'Natural Frequency');  
    fn_sqrt2 = fn * sqrt(2);
    plot([fn_sqrt2, fn_sqrt2], [0, max(best_T)], 'g--', 'LineWidth', 1.5, 'DisplayName', '√2×Natural Frequency');

    xlabel('Frequency (Hz)');
    ylabel('Transmission Ratio |T|');
    title(sprintf('Frequency Response Curve (c=%.2f N·s/m, \\zeta=%.4f)', best_c, best_zeta), 'FontSize', 16);
    text(0.5, 0.8, '$T = \frac{\sqrt{1 + (2\zeta r)^2}}{\sqrt{(1 - r^2)^2 + (2\zeta r)^2}}$', ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    legend('Transmission Ratio', 'Natural Frequency', '√2×Natural Frequency', ...
        'Location', 'best', 'Interpreter', 'none', 'FontSize', 12);
    grid on;
    xlim([0.1, 100]);
    ylim([0, max(best_T) * 1.1]);

    % === Figure 2: Transmission Energy vs Damping Coefficient ===
    figure('Name', 'Energy vs Damping Coefficient', 'Units', 'inches', 'Position', figSize);
    semilogx(c_range, T_energy_values, 'b-', 'LineWidth', 2);
    hold on;
    plot([best_c, best_c], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
    xlabel('Damping Coefficient c (N·s/m)');
    ylabel('Transmission Energy E (0–100 Hz)');
    title('Energy vs. Damping Coefficient', 'FontSize', 16);
    text(0.05, 0.85, '$E = \int_{0}^{100} T^2(f) df$', ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.75, sprintf('$c_{best} = %.2f$ N$\\cdot$s/m', best_c), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.65, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    legend('Transmission Energy', 'Optimal Damping Coefficient', 'Location', 'best', 'FontSize', 12);
    grid on;

    % === Figure 3: Transmission Energy vs Damping Ratio ===
    figure('Name', 'Energy vs Damping Ratio', 'Units', 'inches', 'Position', figSize);
    plot(zeta_values, T_energy_values, 'b-', 'LineWidth', 2);
    hold on;
    plot([best_zeta, best_zeta], [min(T_energy_values), max(T_energy_values)], 'r--', 'LineWidth', 1.5);
    xlabel('Damping Ratio \zeta');
    ylabel('Transmission Energy E (0–100 Hz)');
    title('Energy vs. Damping Ratio', 'FontSize', 16);
    text(0.05, 0.85, '$E = \int_{0}^{100} T^2(f) df$', ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    text(0.05, 0.75, sprintf('$\\zeta_{best} = %.4f$', best_zeta), ...
        'Interpreter', 'latex', 'FontSize', 14, 'Units', 'normalized');
    legend('Transmission Energy', 'Optimal Damping Ratio', 'Location', 'best', 'FontSize', 12);
    grid on;
    % === Time-Domain Comparison ===
    fig_time = figure('Name', 'Time-Domain Comparison of Acceleration', 'Units', 'inches', 'Position', figSize);
    acc_base_g_detrend = acc_base / g;
    plot(time, acc_base_g_detrend, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Before Isolation (detrended)'); 
    hold on;
    plot(time, acc_isolated / g, 'r-', 'LineWidth', 1.5, 'DisplayName', 'After Isolation (simulated)'); 
    xlabel('Time (s)');
    ylabel('Acceleration (g)');
    title('Time-Domain Acceleration Comparison', 'FontSize', 16);
    legend('show', 'Location', 'best', 'FontSize', 12);
    grid on;
    xlim([min(time), max(time)]);

    % === PSD and LPSD Computation ===
    nfft = 100000;
    window = hanning(nfft);
    overlap = round(0.5 * nfft);

    [pxx_base, f] = pwelch(acc_base, window, overlap, nfft, fs);
    [pxx_isolated, ~] = pwelch(acc_isolated, window, overlap, nfft, fs);

    lpsd_base = sqrt(pxx_base) / g;
    lpsd_isolated = sqrt(pxx_isolated) / g;

    lpsd_base_disp = g ./ ((2*pi*f).^2) .* lpsd_base;
    lpsd_isolated_disp = g ./ ((2*pi*f).^2) .* lpsd_isolated;

    % === PSD Plot ===
    fig_psd = figure('Name', 'PSD Comparison', 'Units', 'inches', 'Position', figSize);
    loglog(f, pxx_base / g^2, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Before Isolation');
    hold on;
    loglog(f, pxx_isolated / g^2, 'r-', 'LineWidth', 1.5, 'DisplayName', 'After Isolation');
    xlabel('Frequency (Hz)');
    ylabel('PSD [g²/Hz]');
    title('Power Spectral Density Comparison', 'FontSize', 16);
    legend('show', 'Location', 'best', 'FontSize', 12);
    grid on;
    xlim([0.1, 200]);

    % === LPSD Acceleration ===
    fig_acc_lpsd = figure('Name', 'LPSD of Acceleration', 'Units', 'inches', 'Position', figSize);
    loglog(f, lpsd_base, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Before Isolation');
    hold on;
    loglog(f, lpsd_isolated, 'r-', 'LineWidth', 1.5, 'DisplayName', 'After Isolation');
    xlabel('Frequency (Hz)');
    ylabel('LPSD [g/√Hz]');
    title('Linear Power Spectral Density of Acceleration', 'FontSize', 16);
    legend('show', 'Location', 'best', 'FontSize', 12);
    grid on;
    xlim([0.1, 200]);

    % === LPSD Displacement ===
    fig_disp_lpsd = figure('Name', 'LPSD of Displacement', 'Units', 'inches', 'Position', figSize);
    loglog(f, lpsd_base_disp * 1e9, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Before Isolation');
    hold on;
    loglog(f, lpsd_isolated_disp * 1e9, 'r-', 'LineWidth', 1.5, 'DisplayName', 'After Isolation');
    xlabel('Frequency (Hz)');
    ylabel('LPSD [nm/√Hz]');
    title('Linear Power Spectral Density of Displacement', 'FontSize', 16);
    legend('show', 'Location', 'best', 'FontSize', 12);
    grid on;
    xlim([0.1, 200]);
    % === RMS Calculation ===
    band_edges = [0.1, 40; 0.1, 100; 1, 40; 40, 100; 1, 100];
    band_names = {'[0.1–40] Hz', '[0.1–100] Hz', '[1–40] Hz', '[40–100] Hz', '[1–100] Hz'};
    df = mean(diff(f));  
    nBands = length(band_names);  
    RMS_base_acc = zeros(1, nBands);
    RMS_isolated_acc = zeros(1, nBands);
    RMS_base_disp = zeros(1, nBands);
    RMS_isolated_disp = zeros(1, nBands);

    for iBand = 1:nBands
        idx = (f >= band_edges(iBand, 1) & f <= band_edges(iBand, 2));
        RMS_base_acc(iBand) = sqrt(sum((lpsd_base(idx) .^ 2) * df)) * 1e6;
        RMS_isolated_acc(iBand) = sqrt(sum((lpsd_isolated(idx) .^ 2) * df)) * 1e6;
        RMS_base_disp(iBand) = sqrt(sum((lpsd_base_disp(idx) .^ 2) * df)) * 1e9;
        RMS_isolated_disp(iBand) = sqrt(sum((lpsd_isolated_disp(idx) .^ 2) * df)) * 1e9;
    end

    reduction_acc = (RMS_base_acc - RMS_isolated_acc) ./ RMS_base_acc * 100;
    reduction_disp = (RMS_base_disp - RMS_isolated_disp) ./ RMS_base_disp * 100;

    % === Create Table Data ===
    rms_results = cell(nBands, 7);
    for iBand = 1:nBands
        rms_results{iBand,1} = band_names{iBand};
        rms_results{iBand,2} = sprintf('%.2f', RMS_base_acc(iBand));
        rms_results{iBand,3} = sprintf('%.2f', RMS_isolated_acc(iBand));
        rms_results{iBand,4} = sprintf('%.1f%%', reduction_acc(iBand));
        rms_results{iBand,5} = sprintf('%.2f', RMS_base_disp(iBand));
        rms_results{iBand,6} = sprintf('%.2f', RMS_isolated_disp(iBand));
        rms_results{iBand,7} = sprintf('%.1f%%', reduction_disp(iBand));
    end

    % === Table Column Names ===
    col_names = {'Frequency Band', 'Before Acc (μg)', 'After Acc (μg)', 'Reduction (%)', ...
                 'Before Disp (nm)', 'After Disp (nm)', 'Reduction (%)'};

    % === Filter Out Hidden Bands ===
    display_idx = [3, 4, 5];  % Skip 0.1–40 and 0.1–100
    fig_rms = figure('Name', 'RMS Comparison Table', 'Units', 'inches', 'Position', figSize);
    uitable(fig_rms, 'Data', rms_results(display_idx, :), ...
                   'ColumnName', col_names, ...
                   'Units', 'normalized', 'Position', [0.05, 0.05, 0.9, 0.9], ...
                   'FontSize', 10, 'RowName', []);

    % === Command Line Output ===
    fprintf('\n=== RMS Comparison Summary ===\n');
    fprintf('%-18s %-20s %-20s %-15s %-20s %-20s %-15s\n', ...
        'Frequency Band', 'Before Acc (μg)', 'After Acc (μg)', 'Reduction (%)', ...
        'Before Disp (nm)', 'After Disp (nm)', 'Reduction (%)');
    fprintf('-------------------------------------------------------------------------------------------------------------\n');
    for iBand = display_idx
        fprintf('%-18s %-20.2f %-20.2f %-15.1f %-20.2f %-20.2f %-15.1f\n', ...
            band_names{iBand}, ...
            RMS_base_acc(iBand), RMS_isolated_acc(iBand), reduction_acc(iBand), ...
            RMS_base_disp(iBand), RMS_isolated_disp(iBand), reduction_disp(iBand));
    end
else
    disp('No design found meeting all constraints.');
end
