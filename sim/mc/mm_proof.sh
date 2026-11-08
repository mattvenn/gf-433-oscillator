#!/bin/bash
# Proof that gf180mcuD mismatch is per instance in ngspice: 4 identical nfet_03v3 (1.2/5.333 um, the DAC unit) at
# vgs 1.0 V, vds 1.9 V, with sw_stat_mismatch=1 (global off), two seeds; plus mismatch off as the control.
# Usage (repo root): tools/osic-mac bash sim/mc/mm_proof.sh
set -eu
D=build/mc/proof; mkdir -p $D; cd $D
printf 'set ng_nomodcheck\nset num_threads=1\noption noinit\n' > .spiceinit
for mm in 0 1; do for seed in 11 12; do
cat > p_${mm}_${seed}.cir <<EOC
* mismatch proof mm=$mm seed=$seed
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice typical
.param sw_stat_mismatch=$mm
.options seed=$seed
vg g 0 1.0
vd d 0 1.9
$(for i in 1 2 3 4; do echo "vm$i d d$i 0"; echo "XM$i d$i g 0 0 nfet_03v3 w=1.2u l=5.333u"; done)
.control
op
echo "I mm=$mm seed=$seed \$&i(vm1) \$&i(vm2) \$&i(vm3) \$&i(vm4)"
quit
.endc
.end
EOC
ngspice -b p_${mm}_${seed}.cir 2>&1 | grep "^I mm"
done; done
