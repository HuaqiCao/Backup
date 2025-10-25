% ---------- Parameters ---------------------------------------------------
m1 = 0.004;     % kg
m2 = 0.016;     % kg
k1 = 53;        % N/m
k2 = 212;       % N/m
c1 = 0.01;      % N*s/m
c2 = 0.01;      % N*s/m

fmax = 250;            % max frequency [Hz] (set 250 or 1500 to match figure)
Npts = 30000;           % frequency samples
f = linspace(0, fmax, Npts);
omega = 2*pi*f;         % angular frequency ω [rad/s]

%% ---------- Definitions (as in the paper "Where:") ----------------------
mu     = m1/m2;                      % μ = m1/m2
omega1 = sqrt(k1/m1);                % ω1^2 = k1/m1  -> ω1
omega2 = sqrt(k2/m2);                % ω2^2 = k2/m2  -> ω2
alpha  = omega2/omega1;              % α = ω2/ω1
zeta1  = c1/(2*sqrt(k1*m1));         % ζ1 = c1 / (2√(k1 m1))
zeta2  = c2/(2*sqrt(k2*m2));         % ζ2 = c2 / (2√(k2 m2))
wbar1  = omega/omega1;               % \bar{ω}_1 = ω / ω1

%% ---------- Eq.(6): A, B, and T_D --------------------------------------
A = wbar1.^4 ...
  - wbar1.^2 .* (alpha.^2 + 4*zeta1*zeta2*alpha + mu + 1) ...
  + alpha.^2;

B = wbar1.^3 .* (2*zeta2*alpha + 2*zeta1*mu + 2*zeta1) ...
  - wbar1 .* (2*zeta1*alpha.^2 + 2*zeta2*alpha);

num1 = (alpha.^2 - 4*zeta1*zeta2*alpha .* wbar1.^2).^2;
num2 = (wbar1.^2 .* (2*zeta1*alpha.^2 + 2*zeta2*alpha)).^2;
den  = A.^2 + B.^2;

T_D = sqrt(num1 + num2) ./ sqrt(den);      % linear magnitude
T_D_dB = 20*log10(T_D + eps);               % dB (avoid -Inf at exact zeros)

%% ---------- Plot (paper-like style) -------------------------------------
fig = figure('Color','w');
ax  = axes(fig);

plot(f, T_D_dB, 'k', 'LineWidth', 1.4); hold on;

% Light dotted grid like the article
ax.FontName = 'Times New Roman';
ax.FontSize = 12;
ax.LineWidth = 1;
grid(ax, 'on');
ax.GridLineStyle = ':';                 % dotted grid
ax.MinorGridLineStyle = ':';           
ax.GridColor = [0 0 0];                 % grey-ish via alpha
ax.GridAlpha = 0.15;                    % lighter grid
ax.MinorGridAlpha = 0.10;
ax.XMinorGrid = 'off';
ax.YMinorGrid = 'off';

xlim([0 fmax]);
xlabel('Vibration Frequency (Hz)', 'FontSize', 13);
ylabel('Transmissibility (dB)', 'FontSize', 13);
title('Transmissibility', 'FontSize', 13);

%% ---------- Mark resonance peaks (two dominant maxima) ------------------
% Detect peaks on the dB curve (tune prominence slightly if needed)
[pk, locIdx] = findpeaks(T_D_dB, 'MinPeakProminence', 3, 'MinPeakDistance', round(Npts*0.005));
f_peaks = f(locIdx);
pk_vals = pk;

% Keep the first two strongest peaks (typical for a 2-DOF isolator)
if numel(pk_vals) >= 2
    [~, order] = sort(pk_vals, 'descend');
    sel = sort(order(1:2)); % keep index in ascending frequency order
    f_peaks = f_peaks(sel);
    pk_vals = pk_vals(sel);
end

% Plot dots and vertical dotted lines + labels
for i = 1:numel(f_peaks)
    plot(f_peaks(i), pk_vals(i), 'ko', 'MarkerFaceColor','k', 'MarkerSize', 4);
    xline(f_peaks(i), ':k', 'LineWidth', 1);            % vertical dotted line
    text(f_peaks(i)+8, pk_vals(i), sprintf('%.1f Hz', f_peaks(i)), ...
        'FontSize', 10, 'Color', 'k');
end

% Optional: tighten y-limits a bit but leave headroom
yl = ylim;
ylim([yl(1), max( pk_vals(~isnan(pk_vals)) ) + 5]);

disp('Done: paper-style Transmissibility (dB) vs Vibration Frequency (Hz).');

%% Natural frequencies (undamped resonances)
omega_n = sqrt( ...
    (m2*k1 + m1*(k1 + k2) + [-1 1] .* ...
    sqrt((m2*k1 + m1*(k1 + k2))^2 - 4*m1*m2*k1*k2)) ...
    ./ (2*m1*m2) );

f_n = omega_n / (2*pi);   % convert to Hz

fprintf('Resonant frequencies (undamped): f1 = %.2f Hz, f2 = %.2f Hz\n', f_n(1), f_n(2));
