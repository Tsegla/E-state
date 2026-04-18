import { BackOfficeShell } from "@/components/back-office-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";

export default function LegalPage() {
  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <div>
          <h1 className="text-display text-ink">{uk.nav.legal}</h1>
          <p className="text-small">
            Повна версія — у файлі <code>docs/legal-compliance.md</code>.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-h2">Коротко</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-ink">
            <p>
              Платформа обробляє тільки ті дані, які громада отримує офіційно з ДЗК та ДРРП відповідно до
              підстав, передбачених Законом «Про місцеве самоврядування» та Законом «Про захист
              персональних даних».
            </p>
            <p>
              РНОКПП (податковий номер платника) маскується у всіх інтерфейсах та логах. Повний номер
              видимий лише користувачам з роллю інспектора чи землевпорядника у рамках офіційної перевірки.
            </p>
            <p>
              Кожне звернення до даних особи записується до журналу аудиту. Громадяни можуть направляти
              запити згідно із Законом «Про доступ до публічної інформації».
            </p>
          </CardContent>
        </Card>
      </div>
    </BackOfficeShell>
  );
}
