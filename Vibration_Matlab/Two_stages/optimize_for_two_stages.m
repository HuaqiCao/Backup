% ============================================================
% 本程序用于：优化“两级隔振系统”参数（m1,k1,c1,k2,c2），并输出
% 1）最优两级隔振的传递率（含单级对比、无阻尼对比）
% 2）输入/输出加速度 PSD、位移 PSD、LPSD
% 3）多个频段的 RMS（μg / nm），并写入 Excel
% 4）控制台打印 RMS 对比表
%
% 流程概要：
% ------------------------------------------------------------
% 1. 读取加速度传感器 CSV（v → a）
% 2. 根据 PSD 优化两级隔振参数（fminsearch）
% 3. 得到优化后的系统传递函数 X2/X0
% 4. 计算隔振后 PSD
% 5. 计算 RMS（分频段）
% 6. 生成四个图：传递率、PSD、加速度 LPSD、位移 LPSD
% 7. 保存 Excel（无竖线列、无多余标题）
% ============================================================

function optimize_for_two_stages()
% Two-stage isolation: optimize + PSD/LPSD + Excel RMS + console

% ---- 全局 LaTeX 渲染设置 ----
set(groot,'defaultTextInterpreter','latex', ...
          'defaultAxesTickLabelInterpreter','latex', ...
          'defaultLegendInterpreter','latex', ...
          'defaultAxesFontName','Arial', ...
          'defaultTextFontName','Arial', ...
          'defaultLegendFontName','Arial', ...
          'defaultAxesFontSize',12);

%% ---- I/O：选择 CSV ----
[filename, pathname] = uigetfile({'*.csv','CSV Files (*.csv)'}, 'Select CSV');
if isequal(filename,0), error('Canceled.'); end
raw = readmatrix(fullfile(pathname, filename), 'NumHeaderLines', 4);
t = raw(:,1); v = raw(:,2);

%% ---- 常量 ----
gain=100; sens=1.026; g0=9.80665; m2=12.6; delta_max=0.30;

% 优化的加权 RMS 频段
bands_opt = [1 40; 1 100];
weights   = [1.5, 0.5];

% 输出表格用的频段
bands_table = [1 40; 40 1000; 1 1000];
band_labels = {'[1--40) Hz','(40--1000] Hz','[1--1000] Hz'};

%% ---- 计算输入 PSD（v→a） ----
dt = median(diff(t)); fs = 1/dt;
a_ms2 = (v./(gain* sens))*g0;     % v→g→m/s^2
a_ms2 = a_ms2 - mean(a_ms2);      % 去直流
N = numel(a_ms2);

seglen = max(256, min(round(fs*10), N));      % Welch 段长
window = hamming(seglen,'periodic'); 
overlap = round(seglen/2); 
nfft=seglen;

[Sa, f] = pwelch(a_ms2, window, overlap, nfft, fs, 'psd');
df_print = (numel(f)>1) * mean(diff(f));

% 截掉 1 Hz 以下
keep = f >= 1.0; f=f(keep); Sa=Sa(keep); w=2*pi*f;

%% ---- 边界 + 优化函数 ----
m1_lb=0.1; m1_ub=200.0; 
k1_lb=1; k1_ub=5e5; 
k2_lb=100; k2_ub=1e6;
z1_lb=0.001; z1_ub=0.5; 
z2_lb=0.001; z2_ub=0.5;

% y-space 映射（fminsearch 使用）
lb=[m1_lb,k1_lb,k2_lb,z1_lb,z2_lb]; 
ub=[m1_ub,k1_ub,k2_ub,z1_ub,z2_ub];
toY=@(x) log((x-lb)./(ub-x));           % x→y
toX=@(y) lb+(ub-lb).*(1./(1+exp(-y)));  % y→x

% 初始点
x0=[3, 5e3, max(3e4,1.2*k2_lb), 0.05, 0.05];
x0=min(max(x0,lb+1e-6*(ub-lb)), ub-1e-6*(ub-lb)); 
y0=toY(x0);

% 优化目标（RMS + 惩罚）
objY=@(y)objective_in_y(y,toX,m2,f,w,Sa,bands_opt,weights,delta_max,g0);
opts=optimset('Display','off','TolX',1e-6,'TolFun',1e-6,'MaxIter',5e4);

[y_opt,~]=fminsearch(objY,y0,opts);
x_opt=toX(y_opt); 
m1=x_opt(1); k1=x_opt(2); k2=x_opt(3); z1=x_opt(4); z2=x_opt(5);

c1=2*z1*sqrt(k1*m1); 
c2=2*z2*sqrt(k2*m2);

% 打印优化后的参数
fprintf('=== Optimized Parameters ===\n');
fprintf('m1 = %.4f kg | m2 = %.4f kg\n',m1,m2);
fprintf('k1 = %.4e N/m | k2 = %.4e N/m\n',k1,k2);
fprintf('c1 = %.4f Ns/m | c2 = %.4f Ns/m\n\n',c1,c2);

%% ---- 隔振前后 PSD（加速度/位移） ----
G = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*w);   % X2/X0
Sa_after = (abs(G).^2).*Sa;               % 输出加速度 PSD
Sd_before= Sa./(w.^4);                    % 位移 PSD
Sd_after = Sa_after./(w.^4);

%% ---- 求两级系统的无阻尼固有频率 ----
A = m1*m2; 
B = m1*(k1+k2) + m2*k1; 
C = k1*k2;
disc = max(B.^2 - 4*A*C, 0);
w1 = sqrt( max((B - sqrt(disc))/(2*A),0) );
w2 = sqrt( max((B + sqrt(disc))/(2*A),0) );
f1_nat = w1/(2*pi); 
f2_nat = w2/(2*pi);

%% ---- 图1：位移传递率（含单级对比） ----
%（仅颜色注释）
col2 = [0.12 0.32 0.86];  % 两级
col1 = [0.90 0.45 0.10];  % 单级

fT = logspace(-1, 4, 10000); 
wT=2*pi*fT;

% 两级（有阻尼、无阻尼）
Tmag  = abs( tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*wT) );
T_dB  = 20*log10(Tmag);
T0_dB = 20*log10( abs( tf_Gjw_vec(k1,k2,0,0,m1,m2,1i*wT) ) );

% 单级
mS=12.6; kS=563.12; cS=85.20; 
zetaS=cS/(2*sqrt(kS*mS));
rS=(2*pi*fT)/sqrt(kS/mS);
TS  = sqrt( (1+(2*zetaS.*rS).^2)./((1-rS.^2).^2+(2*zetaS.*rS).^2) );
TS0 = sqrt( 1 ./ ((1-rS.^2).^2) );
TS_dB  = 20*log10(TS);
TS0_dB = 20*log10(TS0);
f_nS = sqrt(kS/mS)/(2*pi);

figure('Name','Displacement Transmissibility','Units','inches',...
       'Position',[1,1,10,5],'Color','w');
ax1=gca; hold on; grid on; box on;

% 绘制两级/单级（内容不变）
h2d = semilogx(fT, T_dB, 'LineWidth', 2.6, 'Color', col2);
h2u = semilogx(fT, T0_dB,'--','LineWidth', 2.0,'Color', col2);
h1d = semilogx(fT, TS_dB, 'LineWidth', 2.2, 'Color', col1);
h1u = semilogx(fT, TS0_dB,'--','LineWidth', 1.8,'Color', col1);

% 固有频率标记线
yl = ylim; ylo=yl(1); yhi=yl(2);
short_vline(ax1, f1_nat, ylo+0.40*(yhi-ylo), yhi, '--', [0.5 0.5 0.5], 1.0);
short_vline(ax1, f2_nat, ylo+0.40*(yhi-ylo), yhi, '--', [0.5 0.5 0.5], 1.0);
short_vline(ax1, f_nS,   ylo+0.40*(yhi-ylo), yhi, ':',  col1,           1.2);

xlabel('Frequency (Hz)','FontSize',16);
ylabel('$T$ (dB)','FontSize',16);
title('Single vs Two-stage','FontSize',22);
set(ax1,'XScale','log');

legend('Two-stage','Two-stage (undamped)', ...
       'Single-stage','Single-stage (undamped)', ...
       'Location','best');

%% ---- 计算频段 RMS ----
[rmsA_after, rmsD_after]   = integ_bands(f, Sa_after, Sd_after, bands_table);
[rmsA_before, rmsD_before] = integ_bands(f, Sa,       Sd_before, bands_table);

acc_uG_before = rmsA_before/g0*1e6;     % μg
acc_uG_after  = rmsA_after /g0*1e6;
disp_nm_before= rmsD_before*1e9;        % nm
disp_nm_after = rmsD_after *1e9;

reduction_acc  = 100*(acc_uG_after./acc_uG_before - 1);
reduction_disp = 100*(disp_nm_after./disp_nm_before - 1);

%% ---- 控制台打印输出 ----
fprintf('=== RMS Comparison — %s ===\n', filename);
fprintf('%-16s %-17s %-17s %-17s | %-17s %-17s %-17s\n', ...
    'Frequency Band','Before Acc (\xB5g)','After Acc (\xB5g)','Change (%)', ...
    'Before Disp (nm)','After Disp (nm)','Change (%)');

for i=1:numel(band_labels)
    fprintf('%-16s %-17.2f %-17.2f %-17.2f | %-17.2f %-17.2f %-17.2f\n', ...
        band_labels{i}, acc_uG_before(i), acc_uG_after(i), reduction_acc(i), ...
        disp_nm_before(i), disp_nm_after(i), reduction_disp(i));
end

%% ---- 图2：加速度 PSD ----
figure('Name','Acceleration PSD (SI)','Units','inches','Position',[1,1,10,5],'Color','w');
loglog(f, Sa/g0^2, 'LineWidth',1.8); hold on; grid on;
loglog(f, Sa_after/g0^2,'--','LineWidth',1.8);
xlabel('Frequency (Hz)');
ylabel('PSD $[\mathrm{g}^2/\mathrm{Hz}]$');
title(sprintf('Power Spectral Density (\\Delta f=%.1f Hz)', df_print));

%% ---- 图3：加速度 LPSD ----
figure('Name','Acceleration LPSD','Units','inches','Position',[1,1,10,5],'Color','w');
lpsd_before_g = sqrt(Sa)/g0; 
lpsd_after_g = sqrt(Sa_after)/g0;
loglog(f, lpsd_before_g, 'LineWidth',1.8); hold on; grid on;
loglog(f, lpsd_after_g,'--','LineWidth',1.8);
xlabel('Frequency (Hz)');
ylabel('LPSD $[\mathrm{g}/\sqrt{Hz}]$');
title(sprintf('Acceleration LPSD (\\Delta f=%.1f Hz)', df_print));

%% ---- 图4：位移 LPSD ----
figure('Name','Displacement LPSD','Units','inches','Position',[1,1,10,5],'Color','w');
lpsd_before_nm = sqrt(Sd_before)*1e9; 
lpsd_after_nm  = sqrt(Sd_after)*1e9;
loglog(f, lpsd_before_nm, 'LineWidth',1.8); hold on; grid on;
loglog(f, lpsd_after_nm,'--','LineWidth',1.8);
xlabel('Frequency (Hz)');
ylabel('LPSD $[\mathrm{nm}/\sqrt{Hz}]$');
title(sprintf('Displacement LPSD (\\Delta f=%.1f Hz)', df_print));

%% ---- 保存 Excel（结构不改，仅注释） ----
mu = char(181);                
en = char(8211);               

hdr = {'Frequency Band', ...
       ['Before Acc (' mu 'g)'], ['After Acc (' mu 'g)'], 'Change (%) (After–Before)', ...
       'Before Disp (nm)', 'After Disp (nm)', 'Change (%)'};

nB = numel(band_labels);
rows = cell(nB, numel(hdr));

for i = 1:nB
    rows{i,1} = band_labels{i};
    rows{i,2} = round(acc_uG_before(i), 3);
    rows{i,3} = round(acc_uG_after(i),  3);
    rows{i,4} = round(reduction_acc(i), 3);
    rows{i,5} = round(disp_nm_before(i), 3);
    rows{i,6} = round(disp_nm_after(i),  3);
    rows{i,7} = round(reduction_disp(i), 3);
end

[~, stem, ~] = fileparts(filename);
nameStem = regexprep(stem,'[^\w\-.]','_');
xlsxPath = fullfile(pathname, sprintf('%s_RMS_summary.xlsx', nameStem));

try
    writecell(hdr,  xlsxPath, 'Sheet', 'RMS_Table', 'Range', 'A1');
    writecell(rows, xlsxPath, 'Sheet', 'RMS_Table', 'Range', 'A2');
    fprintf('\nRMS table saved: %s (sheet: RMS_Table)\n', xlsxPath);
catch ME
    warning('Failed to write XLSX (%s). Fallback to CSV.', ME.message);
    csvPath = fullfile(pathname, sprintf('%s_RMS_summary.csv', nameStem));
    writetable(cell2table([hdr; rows]), csvPath, 'WriteVariableNames', false);
end

end % ===== end 主函数 =====

%% ---------- 以下函数只加中文注释，不改内容 ----------

% 优化目标函数（y-space）
function Jpen = objective_in_y(y,toX,m2,f,w,Sa,bands,weights,delta_max,g0)
x  = toX(y);
m1 = x(1); k1 = x(2); k2 = x(3); z1 = x(4); z2 = x(5);
c1 = 2*z1*sqrt(k1*m1); 
c2 = 2*z2*sqrt(k2*m2);

% 隔振传递函数
G  = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,1i*w);  
Sa_after = (abs(G).^2).*Sa;

% RMS 目标
[rmsA, ~] = integ_bands(f, Sa_after, Sa_after./(w.^4), bands);
J = weights * rmsA(:);

% 静态形变惩罚项
delta1 = (m1+m2)*g0/k1; 
delta2 = m2*g0/k2; 
delta_tot = delta1 + delta2;

penalty = 1e8*( max(0,delta1-0.06).^2 + ...
                max(0,delta2-0.06).^2 + ...
                max(0,delta_tot-delta_max).^2 );

Jpen = J + penalty;
end

% 频段 RMS
function [rmsAccBands,rmsDispBands] = integ_bands(f,Sa_in,Sd_in,bands)
nb = size(bands,1); 
rmsAccBands=zeros(nb,1); 
rmsDispBands=zeros(nb,1);

fmax = max(f);
for i=1:nb
    lo = bands(i,1); 
    hi = min(bands(i,2),fmax);

    if i==1, idx=(f>=lo)&(f< hi);
    elseif i==nb, idx=(f>=lo)&(f<=hi);
    else, idx=(f> lo)&(f<=hi);
    end

    rmsAccBands(i)  = sqrt(trapz(f(idx), Sa_in(idx)));
    rmsDispBands(i) = sqrt(trapz(f(idx), Sd_in(idx)));
end
end

% 两级隔振传递函数 X2/X0
function Gjw = tf_Gjw_vec(k1,k2,c1,c2,m1,m2,jw)
num = (c1*jw + k1).*(c2*jw + k2);
den = (m1*jw.^2 + c1*jw + k1).*(m2*jw.^2 + (c1+c2)*jw + k1 + k2) ...
      - (c1*jw + k1).^2;
Gjw = num ./ den;
end

% 帮助函数：短竖线
function short_vline(ax, x, y1, y2, ls, color, lw)
plot(ax, [x x], [y1 y2], 'LineStyle', ls, ...
     'Color', color, 'LineWidth', lw, 'HandleVisibility','off');
end

% 安全写入 Excel（含退化方案）
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
        writetable(cell2table([wideHdr; wideRow]), csv1,'WriteVariableNames',false);
        writetable(cell2table([longHdr; longRows]), csv2,'WriteVariableNames',false);
        finalPath = sprintf('%s & %s', csv1, csv2);
    end
end
end
