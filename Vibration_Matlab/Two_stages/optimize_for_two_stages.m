function optimize_for_two_stages()
% Two-stage isolation: optimize + PSD/LPSD + Excel RMS + console
% Global LaTeX rendering
set(groot,'defaultTextInterpreter','latex', ...
          'defaultAxesTickLabelInterpreter','latex', ...
          'defaultLegendInterpreter','latex', ...
          'defaultAxesFontName','Arial', ...
          'defaultTextFontName','Arial', ...
          'defaultLegendFontName','Arial', ...
          'defaultAxesFontSize',12);

%% ---- I/O ----
[filename, pathname] = uigetfile({'*.csv','CSV Files (*.csv)'}, 'Select CSV');
if isequal(filename,0), error('Canceled.'); end
raw = readmatrix(fullfile(pathname, filename), 'NumHeaderLines', 4);
t = raw(:,1); v = raw(:,2);

%% ---- Constants ----
gain=100; sens=1.026; g0=9.80665; m2=12.6; delta_max=0.30;

% Objective (acc RMS; weighted)
bands_opt = [1 40; 1 100];
weights   = [1.5, 0.5];

% Reporting bands
bands_table = [1 40; 40 1000; 1 1000];
band_labels = {'[1--40) Hz','(40--1000] Hz','[1--1000] Hz'};

%% ---- PSD of input (v→a) ----
dt = median(diff(t)); fs = 1/dt;
a_ms2 = (v./(gain* sens))*g0; a_ms2 = a_ms2 - mean(a_ms2);
N = numel(a_ms2);
seglen = max(256, min(round(fs*10), N));
window = hamming(seglen,'periodic'); overlap = round(seglen/2); nfft=seglen;
[Sa, f] = pwelch(a_ms2, window, overlap, nfft, fs, 'psd');  % (m/s^2)^2/Hz
df_print = (numel(f)>1) * mean(diff(f));

% Cut low frequency
keep = f >= 1.0; f=f(keep); Sa=Sa(keep); w=2*pi*f;

%% ---- Bounds & optimize ----
m1_lb=0.1; m1_ub=200.0; k1_lb=1; k1_ub=5e5; k2_lb=100; k2_ub=1e6;
z1_lb=0.001; z1_ub=0.5; z2_lb=0.001; z2_ub=0.5;
lb=[m1_lb,k1_lb,k2_lb,z1_lb,z2_lb]; ub=[m1_ub,k1_ub,k2_ub,z1_ub,z2_ub];
toY=@(x) log((x-lb)./(ub-x)); toX=@(y) lb+(ub-lb).*(1./(1+exp(-y)));
x0=[3, 5e3, max(3e4,1.2*k2_lb), 0.05, 0.05];
x0=min(max(x0,lb+1e-6*(ub-lb)), ub-1e-6*(ub-lb)); y0=toY(x0);

objY=@(y)objective_in_y(y,toX,m2,f,w,Sa,bands_opt,weights,delta_max,g0);
opts=optimset('Display','off','TolX',1e-6,'TolFun',1e-6,'MaxIter',5e4);
[y_opt,~]=fminsearch(objY,y0,opts);
x_opt=toX(y_opt); m1=x_opt(1); k1=x_opt(2); k2=x_opt(3); z1=x_opt(4); z2=x_opt(5);
c1=2*z1*sqrt(k1*m1); c2=2*z2*sqrt(k2*m2);

fprintf('=== Optimized Parameters ===\n');
fprintf('m1 = %.4f kg | m2 = %.4f kg\n',m1,m2);
fprintf('k1 = %.4e N/m | k2 = %.4e N/m\n',k1,k2);
fprintf('c1 = %.4f Ns/m | c2 = %.4f Ns/m\n\n',c1,c2);

%% ---- After/Before PSD (acc & disp) ----
G = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*w);         % X2/X0
Sa_after = (abs(G).^2).*Sa;                      % (m/s^2)^2/Hz
Sd_before= Sa./(w.^4); Sd_after = Sa_after./(w.^4);

%% ---- Undamped natural freqs (two-stage) ----
A = m1*m2; B = m1*(k1+k2) + m2*k1; C = k1*k2;
disc = max(B.^2 - 4*A*C, 0);
w1 = sqrt( max((B - sqrt(disc))/(2*A),0) );
w2 = sqrt( max((B + sqrt(disc))/(2*A),0) );
f1_nat = w1/(2*pi); f2_nat = w2/(2*pi);

%% ---- Figure 1: Displacement transmissibility (add single-stage, ζ=0 also) ----
% Colors for Fig.1 only
col2 = [0.12 0.32 0.86];  % two-stage (blue)
col1 = [0.90 0.45 0.10];  % single-stage (orange-like)

fT = logspace(-1, 4, 10000); wT=2*pi*fT;

% Two-stage
Tmag  = abs( tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*wT) );
T_dB  = 20*log10(Tmag);
T0_dB = 20*log10( abs( tf_Gjw_vec(k1,k2,0,0,m1,m2,1i*wT) ) );

% Single-stage params (given by you)
mS=12.6; kS=563.12; cS=85.20; zetaS=cS/(2*sqrt(kS*mS));
rS=(2*pi*fT)/sqrt(kS/mS);
TS  = sqrt( (1+(2*zetaS.*rS).^2)./((1-rS.^2).^2+(2*zetaS.*rS).^2) );
TS0 = sqrt( 1 ./ ((1-rS.^2).^2) );
TS_dB  = 20*log10(TS);
TS0_dB = 20*log10(TS0);
f_nS = sqrt(kS/mS)/(2*pi);

figure('Name','Displacement Transmissibility','Units','inches',...
       'Position',[1,1,10,5],'Color','w');
ax1=gca; hold on; grid on; box on;

% Two-stage (solid/-- same color)
leg_two  = sprintf(['Two-stage $(m_1=%.3g,\\ m_2=%.3g;\\ c_1=%.3g,\\ c_2=%.3g;\\ ' ...
                    'k_1=%.3g,\\ k_2=%.3g)$'], ...
                    m1, m2, c1, c2, k1, k2);

leg_two0 = sprintf('Two-stage (undamped) $(m_1=%.3g,\\ m_2=%.3g;\\ k_1=%.3g,\\ k_2=%.3g)$', ...
                    m1, m2, k1, k2);
h2d = semilogx(fT, T_dB, 'LineWidth', 2.6, 'Color', col2, ...
       'DisplayName', leg_two);

h2u = semilogx(fT, T0_dB, 'LineWidth', 2.0, 'LineStyle','--', ...
       'Color', col2, 'DisplayName','Two-stage (undamped)');

% Single-stage (solid/--)
h1d = semilogx(fT, TS_dB,  'LineWidth', 2.2, 'Color', col1, ...
       'DisplayName', sprintf('Single-stage $(m=%.1f,\\ k=%.2f,\\ c=%.2f)$',mS,kS,cS));
h1u = semilogx(fT, TS0_dB, 'LineWidth', 1.8, 'LineStyle','--', ...
       'Color', col1, 'DisplayName','Single-stage (undamped)');

% Short vertical markers (no labels)
yl = ylim; ylo=yl(1); yhi=yl(2); rng = yhi-ylo;
short_vline(ax1, f1_nat, ylo+0.40*rng, ylo+1.00*rng, '--', [0.5 0.5 0.5], 1.0);
short_vline(ax1, f2_nat, ylo+0.40*rng, ylo+1.00*rng, '--', [0.5 0.5 0.5], 1.0);
short_vline(ax1, f_nS,   ylo+0.40*rng, ylo+1.00*rng, ':',  col1,           1.2);

xlabel('Frequency (Hz)','FontSize',16);
ylabel('$T$ (dB)','FontSize',16);
ttl_df = ''; if df_print>0, ttl_df = sprintf(' $(\\Delta f=%.1f\\,\\mathrm{Hz})$', df_print); end
title(['Single vs Two-stage' ttl_df],'FontSize',22);
set(ax1,'XScale','log','XMinorGrid','on'); xlim([1e-1,1e4]);
set(ax1,'XTick',10.^(-1:4));
legend([h2d,h2u,h1d,h1u],'Location','best','FontSize',12);

%% ---- Band RMS ----
[rmsA_after, rmsD_after]   = integ_bands(f, Sa_after, Sd_after, bands_table);
[rmsA_before, rmsD_before] = integ_bands(f, Sa,       Sd_before, bands_table);

acc_uG_before = rmsA_before/g0*1e6;
acc_uG_after  = rmsA_after /g0*1e6;
disp_nm_before= rmsD_before*1e9;
disp_nm_after = rmsD_after *1e9;

reduction_acc  = 100*(acc_uG_after./acc_uG_before - 1);
reduction_disp = 100*(disp_nm_after./disp_nm_before - 1);

%% ---- Console summary ----
fprintf('=== RMS Comparison — %s ===\n', filename);
fprintf('%-16s %-17s %-17s %-17s | %-17s %-17s %-17s\n', ...
    'Frequency Band','Before Acc (\xB5g)','After Acc (\xB5g)','Change (%)', ...
    'Before Disp (nm)','After Disp (nm)','Change (%)');
for i=1:numel(band_labels)
    fprintf('%-16s %-17.2f %-17.2f %-17.2f | %-17.2f %-17.2f %-17.2f\n', ...
        band_labels{i}, acc_uG_before(i), acc_uG_after(i), reduction_acc(i), ...
        disp_nm_before(i), disp_nm_after(i), reduction_disp(i));
end

%% ---- Fig2: Acceleration PSD (resolution) ----
figure('Name','Acceleration PSD (SI)','Units','inches','Position',[1,1,10,5],'Color','w');
loglog(f, Sa/g0^2, 'LineWidth',1.8, ...
    'DisplayName','Before Isolation on MXC\_vertical @RT'); hold on; grid on; box on;
loglog(f, Sa_after/g0^2,'--','LineWidth',1.8, ...
    'DisplayName','After Isolation on MXC simulation\_vertical @RT');
xlabel('Frequency (Hz)','FontSize',16);
ylabel('PSD $[\mathrm{g}^2/\mathrm{Hz}]$','FontSize',16);
% Fig2 title: ASCII + LaTeX
title(sprintf('Power Spectral Density ($\\Delta f=%.1f\\,\\mathrm{Hz}$)', df_print), ...
      'Interpreter','latex','FontSize',22);
legend('Location','best','FontSize',14,'Interpreter','latex');
xlim([1, max(f)]);

%% ---- Fig3: Acceleration LPSD (resolution) ----
figure('Name','Acceleration LPSD','Units','inches','Position',[1,1,10,5],'Color','w');
lpsd_before_g = sqrt(Sa)/g0; lpsd_after_g = sqrt(Sa_after)/g0;
loglog(f, lpsd_before_g, 'LineWidth',1.8, ...
    'DisplayName','Before Isolation on MXC\_vertical @RT'); hold on; grid on; box on;
loglog(f, lpsd_after_g,  '--','LineWidth',1.8, ...
    'DisplayName','After Isolation on MXC simulation\_vertical @RT');
xlabel('Frequency (Hz)','FontSize',16);
ylabel('LPSD $[\mathrm{g}/\sqrt{\mathrm{Hz}}]$','FontSize',16);
title(sprintf('Acceleration LPSD ($\\Delta f=%.1f\\,\\mathrm{Hz}$)', df_print), ...
      'Interpreter','latex','FontSize',22);
legend('Location','best','FontSize',14,'Interpreter','latex');
xlim([1, max(f)]);

%% ---- Fig4: Displacement LPSD (resolution) ----
figure('Name','Displacement LPSD','Units','inches','Position',[1,1,10,5],'Color','w');
lpsd_before_nm = sqrt(Sd_before)*1e9; lpsd_after_nm = sqrt(Sd_after)*1e9;
loglog(f, lpsd_before_nm, 'LineWidth',1.8, ...
    'DisplayName','Before Isolation on MXC\_vertical @RT'); hold on; grid on; box on;
loglog(f, lpsd_after_nm,  '--','LineWidth',1.8, ...
    'DisplayName','After Isolation on MXC simulation\_vertical @RT');
xlabel('Frequency (Hz)','FontSize',16);
ylabel('LPSD $[\mathrm{nm}/\sqrt{\mathrm{Hz}}]$','FontSize',16);
title(sprintf('Displacement LPSD ($\\Delta f=%.1f\\,\\mathrm{Hz}$)', df_print), ...
      'Interpreter','latex','FontSize',22);
legend('Location','best','FontSize',14,'Interpreter','latex');
xlim([1, max(f)]);

%% ---- Save to Excel (table, no filename row, no '|' column) ----
mu = char(181);                 % 'µ'
en = char(8211);                % en dash ‘–’

% 表头（去掉中间竖线列；Acc 的变化列按你图里写法）
hdr = {'Frequency Band', ...
       ['Before Acc (' mu 'g)'], ['After Acc (' mu 'g)'], 'Change (%) (After–Before)', ...
       'Before Disp (nm)', 'After Disp (nm)', 'Change (%)'};

% 行数据（写“数字”，不是字符串；三位小数，和你截图一致）
nB   = numel(band_labels);
rows = cell(nB, numel(hdr));
for i = 1:nB
    rows{i,1} = band_labels{i};
    rows{i,2} = round(acc_uG_before(i), 3);
    rows{i,3} = round(acc_uG_after(i),  3);
    rows{i,4} = round(reduction_acc(i), 3);   % (after/before-1)*100
    rows{i,5} = round(disp_nm_before(i), 3);
    rows{i,6} = round(disp_nm_after(i),  3);
    rows{i,7} = round(reduction_disp(i), 3);
end

[~, stem, ~] = fileparts(filename);
nameStem = regexprep(stem,'[^\w\-.]','_');
xlsxPath = fullfile(pathname, sprintf('%s_RMS_summary.xlsx', nameStem));

try
    % A1 写表头，A2 起写数据；不再写文件名行与空行
    writecell(hdr,  xlsxPath, 'Sheet', 'RMS_Table', 'Range', 'A1');
    writecell(rows, xlsxPath, 'Sheet', 'RMS_Table', 'Range', 'A2');
    fprintf('\nRMS table saved: %s (sheet: RMS_Table)\n', xlsxPath);
catch ME
    warning('Failed to write XLSX (%s). Fallback to CSV.', ME.message);
    % 退化为 CSV，同样无“|”列、无文件名行
    csvPath = fullfile(pathname, sprintf('%s_RMS_summary.csv', nameStem));
    writetable(cell2table([hdr; rows]), csvPath, 'WriteVariableNames', false);
    fprintf('RMS table saved as CSV: %s\n', csvPath);
end

end
 
%% ---------- Objective (y-space) ----------
function Jpen = objective_in_y(y,toX,m2,f,w,Sa,bands,weights,delta_max,g0)
x  = toX(y);
m1 = x(1); k1 = x(2); k2 = x(3); z1 = x(4); z2 = x(5);
c1 = 2*z1*sqrt(k1*m1); c2 = 2*z2*sqrt(k2*m2);
G  = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*w);   % X2/X0
Sa_after = (abs(G).^2).*Sa;
[rmsA, ~] = integ_bands(f, Sa_after, Sa_after./(w.^4), bands);
J = weights * rmsA(:);                             % objective
% Soft constraints on static deflection
delta1 = (m1+m2)*g0/k1; delta2 = m2*g0/k2; delta_tot = delta1 + delta2;
penalty = 1e8*( max(0,delta1-0.06).^2 + max(0,delta2-0.06).^2 + max(0,delta_tot-delta_max).^2 );
Jpen = J + penalty;
end

%% ---------- Band integration ----------
function [rmsAccBands,rmsDispBands] = integ_bands(f,Sa_in,Sd_in,bands)
nb = size(bands,1); rmsAccBands=zeros(nb,1); rmsDispBands=zeros(nb,1);
fmax = max(f);
for i=1:nb
    lo = bands(i,1); hi = min(bands(i,2),fmax);
    if i==1, idx=(f>=lo)&(f< hi);
    elseif i==nb, idx=(f>=lo)&(f<=hi);
    else, idx=(f> lo)&(f<=hi);
    end
    rmsAccBands(i)  = sqrt(trapz(f(idx), Sa_in(idx)));  % m/s^2
    rmsDispBands(i) = sqrt(trapz(f(idx), Sd_in(idx)));  % m
end
end

%% ---------- Transfer Function X2/X0 ----------
function Gjw = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,jw)
num = (c1*jw + k1).*(c2*jw + k2);
den = (m1*jw.^2 + c1*jw + k1).*(m2*jw.^2 + (c1+c2)*jw + k1 + k2) - (c1*jw + k1).^2;
Gjw = num ./ den;
end

%% ---------- Short vertical line helper (no legend) ----------
function short_vline(ax, x, y1, y2, ls, color, lw)
xs = [x x]; ys = [y1 y2];
plot(ax, xs, ys, 'LineStyle', ls, 'Color', color, 'LineWidth', lw, 'HandleVisibility','off');
end

%% ---------- Robust Excel writer ----------
function finalPath = safe_write_xlsx(xlsxPath, wideHdr, wideRow, longHdr, longRows)
outDir = fileparts(xlsxPath);
if ~isempty(outDir) && ~isfolder(outDir), mkdir(outDir); end
try
    writecell([wideHdr; wideRow], xlsxPath, 'Sheet', 'RMS_Wide');
    writecell([longHdr;  longRows], xlsxPath, 'Sheet', 'RMS_Long');
    finalPath = xlsxPath; return;
catch
    [p,n,~] = fileparts(xlsxPath);
    xlsx2 = fullfile(p, sprintf('%s_%s.xlsx', n, datestr(now,'yyyymmdd_HHMMSS_FFF')));
    try
        writecell([wideHdr; wideRow], xlsx2, 'Sheet', 'RMS_Wide');
        writecell([longHdr;  longRows], xlsx2, 'Sheet', 'RMS_Long');
        finalPath = xlsx2; return;
    catch
        csv1 = fullfile(p, sprintf('%s_RMS_Wide.csv', n));
        csv2 = fullfile(p, sprintf('%s_RMS_Long.csv', n));
        writetable(cell2table([wideHdr; wideRow]), csv1, 'WriteVariableNames', false);
        writetable(cell2table([longHdr;  longRows]), csv2, 'WriteVariableNames', false);
        finalPath = sprintf('%s & %s', csv1, csv2);
    end
end
end
