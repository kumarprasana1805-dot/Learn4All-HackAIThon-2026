document.addEventListener("DOMContentLoaded", () => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Premium entrance choreography. Existing .reveal behavior remains as fallback.
  const reveals = document.querySelectorAll(".reveal");
  reveals.forEach((el, index) => {
    el.style.setProperty("--delay", `${Math.min(index * 65, 520)}ms`);
  });

  if (!reduceMotion && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -30px 0px" });
    reveals.forEach((el) => revealObserver.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("in-view"));
  }

  // Password visibility toggle — preserves the existing login feature.
  document.querySelectorAll("[data-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.toggle);
      if (!input) return;
      input.type = input.type === "password" ? "text" : "password";
      button.textContent = input.type === "password" ? "◉" : "○";
      button.setAttribute("aria-pressed", input.type === "text" ? "true" : "false");
    });
  });

  // Existing welcome auto-redirect.
  const welcome = document.querySelector(".welcome-screen[data-auto-redirect]");
  if (welcome) {
    setTimeout(() => {
      welcome.classList.add("exit");
      setTimeout(() => {
        window.location.href = welcome.dataset.autoRedirect;
      }, 550);
    }, 2100);
  }

  // Animate visible progress bars once, while keeping server-calculated widths intact.
  if (!reduceMotion && "IntersectionObserver" in window) {
    document.querySelectorAll(".progress-track i").forEach((bar) => {
      const finalWidth = bar.style.width;
      if (!finalWidth) return;
      bar.style.setProperty("--final-width", finalWidth);
      bar.style.width = finalWidth;
    });
  }

  // Lightweight button ripple; no navigation or form behavior is intercepted.
  if (!reduceMotion) {
    document.querySelectorAll(".premium-button, .login-submit, .outline-button, .social-login-btn").forEach((button) => {
      button.addEventListener("pointerdown", (event) => {
        const rect = button.getBoundingClientRect();
        const ripple = document.createElement("span");
        ripple.className = "ui-ripple";
        ripple.style.left = `${event.clientX - rect.left}px`;
        ripple.style.top = `${event.clientY - rect.top}px`;
        button.appendChild(ripple);
        setTimeout(() => ripple.remove(), 620);
      });
    });
  }

  // Subtle cursor parallax for the login artwork only.
  const artPanel = document.querySelector(".login-art-panel");
  const artImage = document.querySelector(".login-art-image");
  if (!reduceMotion && artPanel && artImage && window.matchMedia("(pointer:fine)").matches) {
    artPanel.addEventListener("pointermove", (event) => {
      const rect = artPanel.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      artImage.style.transform = `scale(1.045) translate(${x * -7}px, ${y * -5}px)`;
    });
    artPanel.addEventListener("pointerleave", () => {
      artImage.style.transform = "";
    });
  }

  // Auto-dismiss flashes, preserving their existing timing.
  setTimeout(() => {
    document.querySelectorAll(".flash").forEach((el) => {
      el.style.opacity = "0";
      el.style.transform = "translateY(-8px)";
      setTimeout(() => el.remove(), 450);
    });
  }, 4300);
});

/* ===== V13 ULTRA PREMIUM MOTION CONTROLLER ===== */
(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.body.classList.add('v13-page-ready');
  if (reduce) return;

  /* Cursor ambient light: desktop only, intentionally subtle. */
  if (window.matchMedia('(pointer:fine)').matches) {
    let raf = 0;
    window.addEventListener('pointermove', (e) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        document.documentElement.style.setProperty('--mx', `${(e.clientX / innerWidth) * 100}%`);
        document.documentElement.style.setProperty('--my', `${(e.clientY / innerHeight) * 100}%`);
      });
    }, {passive:true});
  }

  /* Gentle 3D tilt. Only existing cards are enhanced; no layout or click behavior changes. */
  const tiltSelectors = '.metric-card,.library-card,.focus-card-premium,.story-card,.impact-card,.next-step-card,.resource-card-premium,.lesson-panel,.profile-panel,.revision-card,.student-row-premium';
  document.querySelectorAll(tiltSelectors).forEach(card => {
    card.classList.add('v13-tilt');
    card.addEventListener('pointermove', e => {
      if (e.pointerType === 'touch') return;
      const r = card.getBoundingClientRect();
      const x = (e.clientX-r.left)/r.width-.5;
      const y = (e.clientY-r.top)/r.height-.5;
      card.style.transform = `perspective(900px) rotateX(${(-y*2.2).toFixed(2)}deg) rotateY(${(x*2.6).toFixed(2)}deg) translateY(-2px)`;
    });
    card.addEventListener('pointerleave', () => { card.style.transform=''; });
  });

  /* Stagger metric cards without changing their server-rendered values. */
  document.querySelectorAll('.metric-card').forEach((el,i)=>{
    el.classList.add('v13-data-ready');
    el.style.setProperty('--metric-delay', `${Math.min(i*90,450)}ms`);
  });

  /* Animate numeric percentage/count text when it is a simple standalone metric. */
  const numberPattern = /^\s*(\d+(?:\.\d+)?)\s*(%?)\s*$/;
  const animateNumber = (el) => {
    if (el.dataset.v13Counted || el.children.length) return;
    const m = el.textContent.match(numberPattern);
    if (!m) return;
    const target = Number(m[1]);
    if (!Number.isFinite(target) || target > 10000) return;
    el.dataset.v13Counted='1';
    const suffix=m[2], start=performance.now(), duration=800;
    const tick=(now)=>{
      const p=Math.min(1,(now-start)/duration), eased=1-Math.pow(1-p,3), value=target*eased;
      el.textContent=(Number.isInteger(target)?Math.round(value):value.toFixed(1))+suffix;
      if(p<1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  document.querySelectorAll('.metric-card strong,.metric-value,.score-number,.report-stat strong').forEach(animateNumber);

  /* Button magnetic micro-motion. */
  document.querySelectorAll('.premium-button,.login-submit,.outline-button,.social-login-btn,.small-gold-button,.logout-pill').forEach(btn=>{
    btn.addEventListener('pointermove',e=>{
      if(e.pointerType==='touch') return;
      const r=btn.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
      btn.style.transform=`translate(${(x*3).toFixed(1)}px,${(y*2).toFixed(1)}px)`;
    });
    btn.addEventListener('pointerleave',()=>{btn.style.transform='';});
  });

  /* Quiz completion / success hooks. Works with existing result buttons/forms without replacing them. */
  const celebrate = () => {
    const target=document.querySelector('.quiz-result,.result-card,.quiz-score,.success-card');
    if(target) target.classList.add('v13-celebrate');
    const cx=innerWidth/2, cy=Math.min(innerHeight*.42,innerHeight-120);
    for(let i=0;i<18;i++){
      const p=document.createElement('i'); p.className='v13-particle';
      p.style.left=`${cx}px`; p.style.top=`${cy}px`;
      const a=(Math.PI*2*i/18)+Math.random()*.2, d=45+Math.random()*110;
      p.style.setProperty('--dx',`${Math.cos(a)*d}px`); p.style.setProperty('--dy',`${Math.sin(a)*d}px`);
      document.body.appendChild(p); setTimeout(()=>p.remove(),950);
    }
  };
  document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',()=>{
    if(form.closest('.quiz-form,.quiz-container,.quiz-card')) setTimeout(celebrate,120);
  }));
  if(document.querySelector('.quiz-result,.result-card')) setTimeout(celebrate,180);
})();
