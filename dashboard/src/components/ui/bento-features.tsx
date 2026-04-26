import React from "react";
import { ScrollReveal } from "./scroll-reveal";

function FeaturesSection() {
  const features = [
    { title: "Autonomous AI Moderation", blurb: "Keeps your server safe by instantly blocking spam, bad language, and trolls without you having to lift a finger.", meta: "Security" },
    { title: "Automated Infrastructure", blurb: "Set up whole servers, text channels, and roles instantly just by describing what you want.", meta: "Automation" },
    { title: "High-Volume Scaling", blurb: "Runs smoothly 24/7, keeping up effortlessly no matter how many thousands of people join your server.", meta: "Scale" },
    { title: "Integrated Monetization", blurb: "Easily accept payments to give your members premium roles and unlock custom features.", meta: "Payments" },
    { title: "Zero-Downtime Reliability", blurb: "Your automated bot never sleeps, ensuring your community stays managed perfectly without interruptions.", meta: "DevOps" },
  ];

  const spans = [
    "md:col-span-2",
    "md:col-span-2",
    "md:col-span-2",
    "md:col-span-3",
    "md:col-span-3",
  ];

  return (
    <div className="w-full relative bg-transparent text-left">
      <section className="relative mx-auto max-w-6xl px-6 py-20 text-white bg-transparent">
        <ScrollReveal>
          <header className="relative mb-10 flex items-end justify-between border-b border-white/20 pb-6">
            <div>
              <h2 className="text-3xl md:text-5xl font-black tracking-tight">Seromod Capabilities</h2>
              <p className="mt-2 text-sm md:text-base text-white/70">
                AI Infrastructure. Fully Automated.
              </p>
            </div>
          </header>
        </ScrollReveal>

        <div className="relative grid grid-cols-1 gap-3 md:grid-cols-6 auto-rows-[minmax(120px,auto)]">
          {features.map((f, i) => (
            <ScrollReveal key={i} className={spans[i]} delay={i * 150}>
              <BentoCard title={f.title} blurb={f.blurb} meta={f.meta} />
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal delay={200}>
          <footer className="relative mt-16 border-t border-white/10 pt-6 text-xs text-white/50 text-left">
            Built to replace human management.
          </footer>
        </ScrollReveal>
      </section>
    </div>
  );
}

function BentoCard({ title, blurb, meta }) {
  return (
    <article
      className="group relative h-full overflow-hidden rounded-2xl border border-white/15 bg-transparent p-5 transition hover:border-white/40 text-left"
    >
      <header className="mb-2 flex items-center gap-3">
        <span className="text-xs text-[#5865F2]">&bull;</span>
        <h3 className="text-base md:text-lg font-semibold leading-tight text-white">
          {title}
        </h3>
        {meta && (
          <span className="ml-auto rounded-full border border-[#5865F2]/40 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[#5865F2]">
            {meta}
          </span>
        )}
      </header>
      <p className="text-sm text-gray-400 max-w-prose">{blurb}</p>

      <div className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute inset-0 rounded-2xl bg-white/5" />
      </div>
    </article>
  );
}

export default FeaturesSection;
export { FeaturesSection };
